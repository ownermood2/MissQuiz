import os
import sys
import logging
import asyncio
import signal
import traceback
from datetime import datetime, timedelta
from keep_alive import start_keep_alive
from app import init_bot
import psutil

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
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

# Global variables for tracking
last_restart = datetime.now()
error_count = 0
MAX_ERRORS = 3  # More aggressive error threshold
RESTART_INTERVAL = timedelta(hours=6)  # More frequent restarts

async def health_check():
    """Perform regular health checks"""
    while True:
        try:
            # Check memory usage
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB

            if memory_usage > 500:  # 500MB threshold
                logger.warning(f"High memory usage detected: {memory_usage}MB")
                os.execv(sys.executable, ['python'] + sys.argv)

            # Check uptime and force restart if needed
            global last_restart
            if datetime.now() - last_restart > RESTART_INTERVAL:
                logger.info("Performing scheduled restart")
                os.execv(sys.executable, ['python'] + sys.argv)

            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds before retrying

async def main():
    """Main async function to run both Flask and bot"""
    global error_count, last_restart

    try:
        # Set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Start keep-alive server first
        start_keep_alive()
        logger.info("Keep-alive server started")

        # Initialize and run bot
        logger.info("Starting Telegram bot...")
        bot = await init_bot()
        logger.info("Bot initialization completed")

        # Check for restart flag and send confirmation
        restart_flag_path = "data/.restart_flag"
        if os.path.exists(restart_flag_path):
            try:
                # Send restart confirmation to OWNER
                from config import OWNER_ID
                from telegram import Bot
                
                token = os.environ.get("TELEGRAM_TOKEN")
                assert token is not None, "TELEGRAM_TOKEN environment variable is required"
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
                
                # Remove the flag file only after successful send
                os.remove(restart_flag_path)
                logger.info(f"Restart confirmation sent to OWNER ({OWNER_ID}) and flag removed")
                
            except Exception as e:
                logger.error(f"Failed to send restart confirmation: {e}")
                logger.info("Flag file kept for retry on next restart")

        # Start health check task
        asyncio.create_task(health_check())

        # Reset error count after successful start
        error_count = 0
        last_restart = datetime.now()

        # Keep the main thread running
        while True:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                error_count += 1

                if error_count >= MAX_ERRORS:
                    logger.critical("Too many errors, performing emergency restart")
                    os.execv(sys.executable, ['python'] + sys.argv)

                continue

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Critical error: {e}\n{traceback.format_exc()}")
        await asyncio.sleep(5)
        os.execv(sys.executable, ['python'] + sys.argv)

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}")
    raise SystemExit("Received termination signal")

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    try:
        # Set up global exception handler
        sys.excepthook = handle_exception

        # Verify environment variables
        required_vars = ["TELEGRAM_TOKEN", "SESSION_SECRET"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
        sys.exit(1)