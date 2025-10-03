import os
import sys
import logging
import asyncio
import threading
from datetime import datetime
from src.core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.INFO)

async def send_restart_confirmation(config: Config):
    """Send restart confirmation to owner if restart flag exists"""
    restart_flag_path = "data/.restart_flag"
    if os.path.exists(restart_flag_path):
        try:
            from telegram import Bot
            
            telegram_bot = Bot(token=config.telegram_token)
            confirmation_message = (
                "✅ Bot restarted successfully and is now online!\n\n"
                f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "⚡ All systems operational"
            )
            
            await telegram_bot.send_message(
                chat_id=config.owner_id,
                text=confirmation_message
            )
            
            os.remove(restart_flag_path)
            logger.info(f"Restart confirmation sent to OWNER ({config.owner_id}) and flag removed")
            
        except Exception as e:
            logger.error(f"Failed to send restart confirmation: {e}")

async def run_polling_mode(config: Config):
    """Run bot in polling mode"""
    from src.core.quiz import QuizManager
    from src.bot.handlers import TelegramQuizBot
    from src.web.app import app
    
    logger.info("Starting in POLLING mode")
    
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=config.port, use_reloader=False, debug=False),
        daemon=True
    )
    flask_thread.start()
    logger.info(f"Flask server started on port {config.port}")
    
    quiz_manager = QuizManager()
    bot = TelegramQuizBot(quiz_manager)
    await bot.initialize(config.telegram_token)
    
    await send_restart_confirmation(config)
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
        await bot.application.stop()

def run_webhook_mode(config: Config):
    """Run bot in webhook mode - initialize bot and export Flask app for gunicorn"""
    from src.web.app import init_bot_webhook
    
    webhook_url = config.get_webhook_url()
    logger.info(f"Initializing WEBHOOK mode with URL: {webhook_url}")
    
    init_bot_webhook(webhook_url)
    logger.info("Webhook bot initialized - ready for gunicorn")
    
    from src.web.app import app
    app.run(host="0.0.0.0", port=config.port)

if __name__ == "__main__":
    try:
        config = Config.load()
        mode = config.get_mode()
        
        if mode == "webhook":
            run_webhook_mode(config)
        else:
            asyncio.run(run_polling_mode(config))
            
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

from src.web.app import app
