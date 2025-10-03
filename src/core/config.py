"""
Configuration file for Telegram Quiz Bot
Store OWNER and WIFU user IDs for access control
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
WIFU_ID = os.environ.get("WIFU_ID")

if OWNER_ID == 0:
    logger.error("OWNER_ID environment variable is not set or invalid!")
    logger.error("Please set OWNER_ID in your environment variables")
    sys.exit(1)

AUTHORIZED_USERS = [OWNER_ID]
if WIFU_ID:
    try:
        WIFU_ID = int(WIFU_ID)
        AUTHORIZED_USERS.append(WIFU_ID)
    except ValueError:
        logger.warning(f"WIFU_ID environment variable is set but invalid: {WIFU_ID}")
        WIFU_ID = None

UNAUTHORIZED_MESSAGE = """╔═════════ 🌹 𝐎𝐧𝐥𝐲 𝐑𝐞𝐬𝐩𝐞𝐜𝐭𝐞𝐝 𝐃𝐞𝐯𝐥𝐨𝐩𝐞𝐫 ═════════╗

👑 𝐓𝐡𝐞 𝐎𝐖𝐍𝐄𝐑 & 𝐇𝐢𝐬 𝐁𝐞𝐥𝐨𝐯𝐞𝐝 𝐖𝐢𝐟𝐮 ❤️🤌  

╚══════════════════════════════════════════════╝"""

DATABASE_PATH = "data/quiz_bot.db"
