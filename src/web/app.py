import os
import logging
import asyncio
from flask import Flask, render_template, jsonify, request
from telegram import Update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

quiz_manager = None
telegram_bot = None

def create_app():
    """Flask app factory - creates and initializes app"""
    global quiz_manager
    
    session_secret = os.environ.get("SESSION_SECRET")
    if not session_secret:
        raise ValueError("SESSION_SECRET environment variable is required")
    
    flask_app = Flask(__name__, 
                template_folder=os.path.join(root_dir, 'templates'),
                static_folder=os.path.join(root_dir, 'static'))
    flask_app.secret_key = session_secret
    
    if quiz_manager is None:
        try:
            from src.core.quiz import QuizManager
            quiz_manager = QuizManager()
            logger.info("Quiz Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Quiz Manager: {e}")
            raise
    
    return flask_app

class _AppProxy:
    """Proxy that defers Flask app creation until first use"""
    def __init__(self):
        self._real_app = None
        self._deferred_registrations = []
    
    def _get_real_app(self):
        """Get or create the real Flask app"""
        if self._real_app is None:
            self._real_app = create_app()
            # Apply all deferred route registrations
            for method_name, args, kwargs, func in self._deferred_registrations:
                getattr(self._real_app, method_name)(*args, **kwargs)(func)
            self._deferred_registrations.clear()
            logger.info("Flask app created and routes registered")
        return self._real_app
    
    def route(self, *args, **kwargs):
        """Defer route registration until app is created"""
        def decorator(func):
            self._deferred_registrations.append(('route', args, kwargs, func))
            return func
        return decorator
    
    def __call__(self, environ, start_response):
        """WSGI callable"""
        return self._get_real_app()(environ, start_response)
    
    def __getattr__(self, name):
        """Proxy all other attributes to real app"""
        return getattr(self._get_real_app(), name)

app = _AppProxy()

def get_app():
    """Get or create Flask app instance"""
    return app._get_real_app()

async def init_bot():
    """Initialize and start the Telegram bot in polling mode"""
    global telegram_bot
    try:
        from src.bot.handlers import TelegramQuizBot

        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")

        telegram_bot = TelegramQuizBot(quiz_manager)
        await telegram_bot.initialize(token)

        logger.info("Telegram bot initialized successfully in polling mode")
        return telegram_bot
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        raise

def init_bot_webhook(webhook_url: str):
    """Initialize bot in webhook mode - called by main.py"""
    global telegram_bot, quiz_manager
    try:
        from src.bot.handlers import TelegramQuizBot
        from src.core.quiz import QuizManager
        
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        
        if quiz_manager is None:
            quiz_manager = QuizManager()
            logger.info("Quiz Manager initialized for webhook mode")
        
        telegram_bot = TelegramQuizBot(quiz_manager)
        asyncio.run(telegram_bot.initialize_webhook(token, webhook_url))
        
        logger.info(f"Webhook bot initialized with URL: {webhook_url}")
        return telegram_bot
    except Exception as e:
        logger.error(f"Failed to initialize webhook bot: {e}")
        raise

@app.route('/')
def health():
    """Simple health check endpoint for deployment platforms"""
    return jsonify({'status': 'ok'})

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint to receive and process Telegram updates"""
    global telegram_bot
    
    try:
        if not telegram_bot or not telegram_bot.application:
            logger.error("Bot not initialized for webhook")
            return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500
        
        update_data = request.get_json(force=True)
        if not update_data:
            return jsonify({'status': 'ok'}), 200
        
        update = Update.de_json(update_data, telegram_bot.application.bot)
        telegram_bot.application.update_queue.put_nowait(update)
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/questions', methods=['GET'])
def get_questions():
    if not quiz_manager:
        return jsonify({"status": "error", "message": "Quiz manager not initialized"}), 500
    return jsonify(quiz_manager.get_all_questions())

@app.route('/api/questions', methods=['POST'])
def add_question():
    try:
        if not quiz_manager:
            return jsonify({"status": "error", "message": "Quiz manager not initialized"}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        question_data = [{
            'question': data['question'],
            'options': data['options'],
            'correct_answer': data['correct_answer']
        }]
        result = quiz_manager.add_questions(question_data)
        return jsonify(result)
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error adding question: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def edit_question(question_id):
    try:
        if not quiz_manager:
            return jsonify({"status": "error", "message": "Quiz manager not initialized"}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        quiz_manager.edit_question(question_id, data)
        return jsonify({"status": "success", "message": "Question updated successfully"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing field: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error editing question {question_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    try:
        if not quiz_manager:
            return jsonify({"status": "error", "message": "Quiz manager not initialized"}), 500
        
        quiz_manager.delete_question(question_id)
        return jsonify({"status": "success", "message": "Question deleted successfully"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
