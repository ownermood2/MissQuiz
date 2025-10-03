import os
import logging
import asyncio
from flask import Flask, render_template, jsonify, request
from telegram import Update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.environ.get("SESSION_SECRET"):
    logger.error("SESSION_SECRET environment variable is required but not set")
    raise ValueError("SESSION_SECRET environment variable must be set for secure session management")

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
app = Flask(__name__, 
            template_folder=os.path.join(root_dir, 'templates'),
            static_folder=os.path.join(root_dir, 'static'))
app.secret_key = os.environ.get("SESSION_SECRET")

try:
    from src.core.quiz import QuizManager
    quiz_manager = QuizManager()
    logger.info("Quiz Manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Quiz Manager: {e}")
    raise

telegram_bot = None

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
    global telegram_bot
    try:
        from src.bot.handlers import TelegramQuizBot
        
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        
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
        asyncio.run(telegram_bot.application.process_update(update))
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/questions', methods=['GET'])
def get_questions():
    return jsonify(quiz_manager.get_all_questions())

@app.route('/api/questions', methods=['POST'])
def add_question():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Convert single question to list format for add_questions method
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
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        quiz_manager.edit_question(question_id, data)
        return jsonify({"status": "success", "message": "Question updated successfully"})
    except ValueError as e:
        # Validation errors
        return jsonify({"status": "error", "message": str(e)}), 400
    except KeyError as e:
        # Missing required fields
        return jsonify({"status": "error", "message": f"Missing field: {str(e)}"}), 400
    except Exception as e:
        # Unexpected errors
        logger.error(f"Error editing question {question_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    try:
        quiz_manager.delete_question(question_id)
        return jsonify({"status": "success", "message": "Question deleted successfully"})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

