"""
Configuration file for Telegram Quiz Bot
Store OWNER and WIFU user IDs for access control
"""

OWNER_ID = 8376823449
WIFU_ID = None

AUTHORIZED_USERS = [OWNER_ID]
if WIFU_ID:
    AUTHORIZED_USERS.append(WIFU_ID)

UNAUTHORIZED_MESSAGE = """╔═════════ 🌹 𝐎𝐧𝐥𝐲 𝐑𝐞𝐬𝐩𝐞𝐜𝐭𝐞𝐝 𝐃𝐞𝐯𝐥𝐨𝐩𝐞𝐫 ═════════╗

👑 𝐓𝐡𝐞 𝐎𝐖𝐍𝐄𝐑 & 𝐇𝐢𝐬 𝐁𝐞𝐥𝐨𝐯𝐞𝐝 𝐖𝐢𝐟𝐮 ❤️🤌  

╚══════════════════════════════════════════════╝"""

DATABASE_PATH = "data/quiz_bot.db"
