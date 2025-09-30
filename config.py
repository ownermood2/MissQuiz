"""
Configuration file for Telegram Quiz Bot
Store OWNER and WIFU user IDs for access control
"""

OWNER_ID = 8376823449
WIFU_ID = None

AUTHORIZED_USERS = [OWNER_ID]
if WIFU_ID:
    AUTHORIZED_USERS.append(WIFU_ID)

UNAUTHORIZED_MESSAGE = "🚫 Only my OWNER & his Wifu can use Developer commands 💎"

DATABASE_PATH = "data/quiz_bot.db"
