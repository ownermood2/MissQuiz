import os
import sys
import logging
import asyncio
import signal
import traceback
import threading
import atexit
from datetime import datetime
from src.web.app import init_bot, init_bot_webhook, app

# Export app for gunicorn (for webhook mode: gunicorn main:app)
app = app

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

# PID lockfile to prevent multiple instances
LOCKFILE = "data/bot.lock"

def acquire_lock():
    """Acquire PID lockfile to prevent multiple bot instances"""
    try:
        if os.path.exists(LOCKFILE):
            # Check if process is still running
            with open(LOCKFILE, 'r') as f:
                old_pid = int(f.read().strip())
            
            try:
                os.kill(old_pid, 0)  # Check if process exists
                logger.error(f"Bot is already running (PID {old_pid}). Only ONE instance allowed!")
                logger.error("To fix: Kill old instance with: kill {old_pid}")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale lockfile
                logger.info(f"Removing stale lockfile (PID {old_pid} no longer exists)")
                os.remove(LOCKFILE)
        
        # Create lockfile with current PID
        os.makedirs('data', exist_ok=True)
        with open(LOCKFILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID lockfile acquired: {os.getpid()}")
        
        # Register cleanup on exit
        atexit.register(release_lock)
        
    except Exception as e:
        logger.error(f"Failed to acquire lockfile: {e}")
        sys.exit(1)

def release_lock():
    """Release PID lockfile on exit"""
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
            logger.info("PID lockfile released")
    except Exception as e:
        logger.debug(f"Error releasing lockfile: {e}")

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

        # Determine operation mode (polling or webhook)
        mode = os.environ.get("MODE", "polling").lower()
        logger.info(f"Bot mode: {mode}")

        if mode == "webhook":
            # Webhook mode - Flask server runs in main thread for gunicorn
            webhook_url = os.environ.get("WEBHOOK_URL")
            if not webhook_url:
                raise ValueError("WEBHOOK_URL environment variable is required when MODE=webhook")
            
            logger.info(f"Starting in WEBHOOK mode with URL: {webhook_url}")
            
            # Initialize bot in webhook mode (starts background event loop thread)
            from src.web.app import init_bot_webhook
            bot = init_bot_webhook(webhook_url)
            logger.info("Bot initialized in webhook mode with persistent event loop")
            
            # Check for restart flag and send confirmation
            await send_restart_confirmation()
            
            # Keep main thread alive (webhook needs persistent background loop)
            logger.info("Webhook mode active - bot running in background event loop")
            logger.info("Flask app should be run with: gunicorn main:app")
            
            # Keep the main thread running to prevent exit
            while True:
                await asyncio.sleep(1)
            
        else:
            # Polling mode (default) - existing behavior
            logger.info("Starting in POLLING mode (default)")
            
            # Start Flask server in background thread
            flask_thread = threading.Thread(target=run_flask_app, daemon=True)
            flask_thread.start()
            logger.info("Flask server started on port 5000")

            # Initialize and run bot
            logger.info("Starting Telegram bot...")
            bot = await init_bot()
            logger.info("Bot initialization completed")

            # Check for restart flag and send confirmation
            await send_restart_confirmation()

            # Keep the main thread running
            logger.info("Bot is running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received, exiting gracefully")
    except Exception as e:
        logger.error(f"Critical error: {e}\n{traceback.format_exc()}")
        raise

async def send_restart_confirmation():
    """Send restart confirmation to owner if restart flag exists"""
    restart_flag_path = "data/.restart_flag"
    if os.path.exists(restart_flag_path):
        try:
            from src.core.config import OWNER_ID
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

if __name__ == "__main__":
    try:
        # Acquire PID lockfile to prevent multiple instances
        acquire_lock()
        
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
