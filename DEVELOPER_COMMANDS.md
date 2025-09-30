# 🔧 Developer Commands Guide

## 🔐 Access Control

Only **OWNER** and **WIFU** (configured in `config.py`) can use developer commands.

- **OWNER_ID**: Set in `config.py` (currently: 8376823449)
- **WIFU_ID**: Set in `config.py` (currently: None)

### Unauthorized Access
If anyone else tries to use developer commands, they will receive:
> 🚫 Only my OWNER & his Wifu can use Developer commands 💎

---

## 📋 Available Commands

### 1. `/delquiz` - Delete Quiz Questions

**Fixed**: No more "Failed to process delete request" errors! ✅

**Usage:**
```
Option 1: Reply to a quiz message with /delquiz
Option 2: /delquiz [quiz_id]
```

**Features:**
- Shows confirmation before deletion
- Displays quiz details (question, options, correct answer)
- Auto-cleans command messages after 5 seconds

**Example:**
```
/delquiz 5
```

Then confirm with:
```
/delquiz_confirm 5
```

---

### 2. `/dev` - Developer Management

**Optimized**: Quick add with just user ID, or use detailed management commands! ⚡

**Quick Add (NEW):**
```
/dev [user_id]         - Instantly add a developer (no "add" keyword needed!)
```

**Detailed Management:**
```
/dev add [user_id]     - Add a developer
/dev remove [user_id]  - Remove a developer
/dev list              - Show all developers with user IDs
```

**Features:**
- **Quick add**: Just `/dev 123456789` - done!
- Display developer names AND user IDs in list
- Cannot remove OWNER or WIFU
- Auto-cleans command messages

**Example:**
```
/dev 123456789         - Quick add (fastest way!)
/dev add 123456789     - Traditional add
/dev list              - See all developers with IDs
/dev remove 123456789
```

---

### 3. `/stats` - Enhanced Statistics Dashboard

**New**: Shows today, this week, this month, and all-time statistics! 📊

**Usage:**
```
/stats
```

**Displays:**
- 📝 **Quiz Activity:**
  - Today's quizzes
  - This week's quizzes
  - This month's quizzes
  - All-time quizzes
  
- 👥 **Users:**
  - Total users
  - Active today
  - Active this week
  
- 👥 **Groups:**
  - Total groups
  
- 📚 **Content:**
  - Total questions
  - Correct answers
  - Success rate

**Interactive Buttons:**
- 🔄 Refresh - Update statistics
- 👥 Top Users - View top performers

---

### 4. `/allreload` - Global Bot Restart

**New**: Restart the bot without downtime ✨

**Usage:**
```
/allreload
```

**Features:**
- Restarts the entire bot process
- Minimal downtime
- Sends confirmation message before restart
- Logs restart action

---

### 5. `/broadband` - Simple Broadcast

**New**: Send plain text broadcasts without forward tags 📢

**Usage:**
```
/broadband [message text]
```

**Features:**
- Sends clean, plain text message
- No forward tags or formatting
- Sends to all users and groups in database
- Confirmation required before sending
- Shows success/failure count

**Example:**
```
/broadband Hello everyone! This is an announcement.
```

Then confirm with:
```
/broadband_confirm
```

**What happens:**
1. Shows confirmation with recipient count
2. After `/broadband_confirm`, sends to all users/groups
3. Reports success/failure statistics

---

### 6. `/broadcast` - Instant Broadcast System

**Optimized**: Lightning-fast broadcast with smart rate limiting! ⚡

**Usage:**

**Option 1: Forward a Message**
```
Reply to any message with /broadcast
```

**Option 2: Send New Message**
```
/broadcast [message text]
```

**Features:**
- **Instant delivery**: Sends to ALL chats immediately
- **Smart rate limiting**: Only adds 0.03s delay for >20 recipients
- **Message tracking**: Tracks each message for accurate deletion
- Reply to a message → Forwards that message to all
- Direct command → Sends new message to all
- Sends to all users and groups
- Confirmation required
- Success/failure reporting

**Example 1 (Forward):**
```
[Reply to a message with] /broadcast
```

**Example 2 (Direct):**
```
/broadcast Important update: Bot will be down for maintenance tonight.
```

Then confirm with:
```
/broadcast_confirm
```

**Performance:**
- Small broadcasts (<20): Instant (no delays)
- Large broadcasts (>20): 0.03s delay per message (prevents Telegram blocks)
- Messages tracked per chat for deletion

---

### 7. `/delbroadcast` - Delete Latest Broadcast

**Optimized**: Delete broadcasts from ANYWHERE - no need to reply! 🗑️

**Usage:**
```
/delbroadcast
```

**Features:**
- **Works from anywhere**: No need to reply to the broadcast
- Deletes latest broadcast from ALL chats instantly
- Uses message tracking for accurate deletion
- Shows how many chats will be affected
- Clear success/failure reporting
- Instant deletion (no delays)

**What happens:**
```
1. /delbroadcast
   Shows: "This will delete the latest broadcast from X chats"
   
2. /delbroadcast_confirm
   Instantly deletes from all chats
   Reports: "Deleted: X, Failed: Y"
```

**Note:**
- Deletions may fail if bot lacks admin permissions in groups
- Messages older than 48 hours cannot be deleted (Telegram limitation)
- Only deletes the LATEST broadcast

---

## ✨ Special Features

### Auto-Clean Messages
All developer commands now **automatically delete** command and reply messages after 5 seconds to keep group chats clean! 🧹

This means:
- Your command message is deleted
- Bot's reply is deleted
- Group stays clean and organized

### Enhanced Error Handling
- Proper error messages for all commands
- Detailed error logging for debugging
- User-friendly error messages

### Group-Friendly
- All commands work in both private chats and groups
- Auto-clean feature keeps groups tidy
- Rate-limited broadcasts prevent spam

### SQLite Database
All data is now stored in SQLite database (`data/quiz_bot.db`):
- ✅ Questions
- ✅ Users & Statistics
- ✅ Developers
- ✅ Groups
- ✅ Quiz History
- ✅ Daily Activity

**Benefits:**
- Faster queries
- Better data integrity
- Easier backup and restore
- Scalable for growth

---

## 📝 Comprehensive Logging

All developer commands now log:
- Who executed the command
- When it was executed
- What action was taken
- Success or failure status

**Log Format:**
```
2025-09-30 08:00:00 - INFO - Developer 8376823449 added developer 123456789
2025-09-30 08:01:00 - INFO - Broadcast completed by 8376823449: 50 sent, 3 failed
2025-09-30 08:02:00 - INFO - Bot restart initiated by user 8376823449
```

---

## 🎯 Quick Reference

| Command | Purpose | Auto-Clean |
|---------|---------|------------|
| `/delquiz [id]` | Delete quiz | ✅ Yes |
| `/dev add/remove/list` | Manage developers | ✅ Yes |
| `/stats` | View statistics | ❌ No |
| `/allreload` | Restart bot | ❌ No |
| `/broadband [text]` | Simple broadcast | ✅ Yes |
| `/broadcast` | Enhanced broadcast | ✅ Yes |

---

## 🔧 Configuration

### Edit `config.py`:
```python
# Set your Telegram user ID
OWNER_ID = 8376823449

# Set Wifu's Telegram user ID (or None)
WIFU_ID = None

# Customize unauthorized message
UNAUTHORIZED_MESSAGE = "🚫 Only my OWNER & his Wifu can use Developer commands 💎"

# Database path
DATABASE_PATH = "data/quiz_bot.db"
```

---

## 📊 Migration from JSON to SQLite

Already completed! ✅

If you need to re-migrate:
```bash
python migrate_to_sqlite.py
```

This will:
- Read all JSON files (questions, users, developers, groups)
- Create SQLite database
- Import all data
- Show migration summary

---

## 🚀 Next Steps

1. **Update WIFU_ID** in `config.py` if needed
2. **Test all commands** in a private chat first
3. **Use `/stats`** to view bot activity
4. **Manage developers** with `/dev` command
5. **Send broadcasts** carefully with confirmation

---

## ⚠️ Important Notes

1. **Broadcast Carefully**: Always confirm before sending broadcasts to avoid spam
2. **Rate Limiting**: Built-in 0.05s delay between messages to prevent Telegram limits
3. **Auto-Clean**: Commands clean up after 5 seconds - normal behavior!
4. **Database Backup**: Backup `data/quiz_bot.db` regularly
5. **Logging**: Check logs for detailed command execution history

---

## 🐛 Troubleshooting

### "/delquiz not working"
- ✅ **FIXED**: Markdown parsing errors resolved
- Use quiz ID from `/editquiz` command
- Confirm deletion with `/delquiz_confirm [id]`

### "Cannot add developer"
- Check that user ID is valid number
- User must have interacted with bot first
- Check logs for error details

### "Broadcast not sending"
- Confirm with `/broadcast_confirm` or `/broadband_confirm`
- Check recipient count in confirmation
- Review logs for failed sends

### "Auto-clean not working"
- This is a feature, not a bug!
- Messages delete after 5 seconds automatically
- Only applies to developer commands

---

**Version**: 2.0.0  
**Last Updated**: September 30, 2025  
**Author**: CV_OWNER  

---

## 💎 Pro Tips

1. Use `/stats` regularly to monitor bot health
2. Test broadcasts with `/broadband` first (simpler)
3. Keep developer list minimal for security
4. Use `/allreload` after major changes
5. Check logs after broadcasts to see delivery status

---

**Need Help?** Check the logs or contact the bot owner!
