import os
import logging
import asyncio
import threading
import traceback
from flask import Flask, render_template, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not os.environ.get("SESSION_SECRET"):
    logger.error("SESSION_SECRET environment variable is required but not set")
    raise ValueError("SESSION_SECRET environment variable must be set for secure session management")

# Initialize Flask with paths relative to project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
app = Flask(__name__, 
            template_folder=os.path.join(root_dir, 'templates'),
            static_folder=os.path.join(root_dir, 'static'))
app.secret_key = os.environ.get("SESSION_SECRET")

# Initialize Quiz Manager
try:
    from src.core.quiz import QuizManager
    quiz_manager = QuizManager()
    logger.info("Quiz Manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Quiz Manager: {e}")
    raise

# Global bot instances - initialized by main.py or auto-initialized in webhook route
telegram_bot = None  # TelegramQuizBot instance
webhook_event_loop = None  # Background asyncio event loop for webhook mode
_bot_ready_event = threading.Event()  # Signals when bot is fully initialized

async def init_bot():
    """Initialize and start the Telegram bot in polling mode"""
    global telegram_bot
    try:
        from src.bot.handlers import TelegramQuizBot

        # Get bot token
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")

        # Initialize bot in polling mode
        telegram_bot = TelegramQuizBot(quiz_manager)
        await telegram_bot.initialize(token)

        logger.info("Telegram bot initialized successfully in polling mode")
        return telegram_bot
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        raise

async def _init_bot_webhook_async(webhook_url: str):
    """Internal async function to initialize bot in webhook mode"""
    global telegram_bot
    try:
        from src.bot.handlers import TelegramQuizBot

        # Get bot token
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")

        # Initialize bot in webhook mode
        telegram_bot = TelegramQuizBot(quiz_manager)
        await telegram_bot.initialize_webhook(token, webhook_url)

        logger.info(f"✅ Telegram bot initialized successfully in webhook mode with URL: {webhook_url}")
        
        # Signal that bot is ready
        _bot_ready_event.set()
        
        logger.info("🎉 Webhook mode ready - handlers will process updates via background event loop")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram bot in webhook mode: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def _run_webhook_event_loop(webhook_url: str):
    """Run the asyncio event loop in a background thread for webhook mode
    
    This function runs in a separate daemon thread and maintains a persistent
    event loop that processes webhook updates submitted via run_coroutine_threadsafe.
    The loop runs forever until the application exits.
    """
    global webhook_event_loop
    try:
        # Create new event loop for this thread
        webhook_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(webhook_event_loop)
        
        logger.info("Starting background event loop for webhook mode")
        
        # Run the bot initialization
        webhook_event_loop.run_until_complete(_init_bot_webhook_async(webhook_url))
        
        # Keep the loop running forever to process incoming updates
        # Updates will be submitted via asyncio.run_coroutine_threadsafe from webhook route
        logger.info("Event loop initialization complete - now running forever to process updates")
        webhook_event_loop.run_forever()
        
    except Exception as e:
        logger.error(f"Error in webhook event loop: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        if webhook_event_loop and not webhook_event_loop.is_closed():
            webhook_event_loop.close()
            logger.info("Webhook event loop closed")

def init_bot_webhook(webhook_url: str):
    """Initialize the Telegram bot in webhook mode with persistent event loop
    
    Creates a background thread with a persistent asyncio event loop that:
    - Initializes the Telegram bot and sets up webhook
    - Processes incoming webhook updates via run_coroutine_threadsafe
    - Runs PTB schedulers and background tasks
    
    Args:
        webhook_url: The public URL where Telegram will send updates
        
    Returns:
        TelegramQuizBot instance
    """
    logger.info(f"Initializing bot in webhook mode with URL: {webhook_url}")
    
    # Clear the ready event in case of re-initialization
    _bot_ready_event.clear()
    
    # Start the event loop in a background daemon thread
    webhook_thread = threading.Thread(
        target=_run_webhook_event_loop,
        args=(webhook_url,),
        daemon=True,
        name="WebhookEventLoop"
    )
    webhook_thread.start()
    
    # Wait for bot to be fully initialized (up to 10 seconds)
    if _bot_ready_event.wait(timeout=10):
        logger.info("Webhook mode initialized successfully - bot is ready")
    else:
        logger.error("Webhook initialization timeout - bot may not be ready")
    
    return telegram_bot

@app.route('/')
def health():
    """Simple health check endpoint for deployment platforms"""
    return jsonify({'status': 'ok'})

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint to receive and process Telegram updates
    
    This endpoint:
    1. Auto-initializes the bot if needed (for gunicorn workers)
    2. Receives JSON updates from Telegram
    3. Dispatches updates to the background event loop for async processing
    4. Returns immediate response to Telegram (required within 60 seconds)
    """
    global telegram_bot, webhook_event_loop
    
    try:
        # Auto-initialize if not already done (handles gunicorn worker initialization)
        if not telegram_bot or not webhook_event_loop:
            webhook_url = os.environ.get("RENDER_URL") or os.environ.get("WEBHOOK_URL")
            if webhook_url:
                logger.info("Worker auto-initializing bot for webhook endpoint")
                init_bot_webhook(webhook_url)
                if not _bot_ready_event.is_set():
                    logger.warning("Bot initialization completed but ready event not set")
        
        # Validate bot is initialized
        if not telegram_bot:
            logger.error("Webhook received but bot is not initialized")
            return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500
        
        if not webhook_event_loop:
            logger.error("Webhook event loop is not running")
            return jsonify({'status': 'error', 'message': 'Event loop not running'}), 500
        
        # Parse incoming update from Telegram
        update_data = request.get_json(force=True)
        
        if not update_data:
            logger.warning("Received empty webhook update")
            return jsonify({'status': 'ok'}), 200
        
        logger.info(f"Processing webhook update: {update_data.get('update_id', 'unknown')}")
        
        # Validate bot application is ready
        if not telegram_bot.application or not telegram_bot.application.bot:
            logger.error("Bot application not properly initialized")
            return jsonify({'status': 'error', 'message': 'Bot not ready'}), 500
        
        # Convert JSON to Telegram Update object
        from telegram import Update
        update = Update.de_json(update_data, telegram_bot.application.bot)
        
        # Dispatch update to background event loop for async processing
        # This allows Flask to respond immediately while PTB processes the update
        asyncio.run_coroutine_threadsafe(
            telegram_bot.application.process_update(update),
            webhook_event_loop
        )
        
        logger.info(f"✅ Dispatched update {update.update_id} to background event loop for processing")
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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

# Auto-initialize webhook mode when running under gunicorn
# This ensures webhook is set up before Telegram sends updates
def _auto_init_webhook_for_gunicorn():
    """Auto-initialize webhook when module is imported by gunicorn"""
    webhook_url = os.environ.get("RENDER_URL") or os.environ.get("WEBHOOK_URL")
    mode = os.environ.get("MODE", "").lower()
    
    # Only auto-init if webhook URL is provided and we're not in polling mode
    if webhook_url and mode != "polling":
        logger.info(f"🚀 Auto-initializing webhook for gunicorn with URL: {webhook_url}")
        try:
            init_bot_webhook(webhook_url)
            logger.info("✅ Webhook initialization completed - bot ready for Telegram updates")
        except Exception as e:
            logger.error(f"❌ Failed to auto-initialize webhook: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

# Run auto-initialization when module is imported (for gunicorn)
# This runs at import time, ensuring webhook is set before first request
if __name__ != "__main__":
    _auto_init_webhook_for_gunicorn()

if __name__ == "__main__":
    """Direct execution for local testing - uses polling mode"""
    try:
        asyncio.run(init_bot())
        app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.exception(f"Application startup failed: {e}")