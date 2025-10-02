import os
import sys
import logging
import asyncio
import signal
import traceback
import threading
from datetime import datetime
from app import init_bot, app

# Configure logging
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
logger.info("Logging configured - httpx set to WARNING to protect bot token")

def run_flask_app():
    """Run Flask server in a separate thread"""
    try:
        app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")
        raise

async def main():
    """Main async function to run both Flask and bot"""
    try:
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            raise SystemExit("Received termination signal")
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start Flask server in background thread
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()
        logger.info("Flask server started on port 5000")

        # Initialize and run bot
        logger.info("Starting Telegram bot...")
        bot = await init_bot()
        logger.info("Bot initialization completed")

        # Check for restart flag and send confirmation
        restart_flag_path = "data/.restart_flag"
        if os.path.exists(restart_flag_path):
            try:
                from config import OWNER_ID
                from telegram import Bot
                
                token = os.environ.get("TELEGRAM_TOKEN")
                if not token:
                    raise ValueError("TELEGRAM_TOKEN environment variable is required")
                
                telegram_bot = Bot(token=token)
                confirmation_message = (
                    "✅ Bot restarted successfully and is now online!\n\n"
                    f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "⚡ All systems operational"
                )
                
                await telegram_bot.send_message(
                    chat_id=OWNER_ID,
                    text=confirmation_message
                )
                
                os.remove(restart_flag_path)
                logger.info(f"Restart confirmation sent to OWNER ({OWNER_ID}) and flag removed")
                
            except Exception as e:
                logger.error(f"Failed to send restart confirmation: {e}")

        # Keep the main thread running
        logger.info("Bot is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received, exiting gracefully")
    except Exception as e:
        logger.error(f"Critical error: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    try:
        # Verify environment variables
        required_vars = ["TELEGRAM_TOKEN", "SESSION_SECRET"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
        sys.exit(1)
