# 🎯 Telegram Quiz Bot

A production-ready Telegram Quiz Bot with automated quiz delivery, real-time statistics tracking, comprehensive analytics, and professional group chat management. Built with Python 3.11+ and designed for seamless deployment on Replit, Render, or Heroku.

## ✨ Features

### Core Features
- 🤖 **Interactive Quiz System**: Poll-based quizzes with instant feedback
- 📊 **Live Statistics Tracking**: Real-time user stats with no caching delays  
- 🎨 **12 Quiz Categories**: Science, History, Geography, Sports, Technology, and more
- ⏰ **Automated Quiz Delivery**: Scheduled quizzes every 30 minutes to active groups
- 👥 **Multi-Platform Support**: Works in private messages and group chats

### Advanced Features
- 📈 **Comprehensive Analytics**: Track user performance, activity logs, and engagement metrics
- 🔄 **Smart Quiz Rotation**: Never repeat questions within the same chat session
- 🎯 **Streak Tracking**: Monitor user answer streaks and performance trends
- 🔐 **Developer Commands**: Advanced admin controls with role-based access
- 📢 **Enhanced Broadcast System**: Send announcements with media, buttons, and dynamic placeholders
- 🧹 **Auto-Cleanup**: Automatically removes old quiz messages for clean chat experience
- 🌐 **Network Resilience**: Automatic reconnection with robust timeout configuration (10s connect, 20s read/write)

### Technical Features
- 💾 **SQLite Database**: Efficient data storage with optimized indexes
- 🔄 **Background Jobs**: 7 automated schedulers for cleanup and monitoring
- 📝 **Activity Logging**: Complete audit trail of all bot interactions
- 🛡️ **Error Handling**: Robust error recovery and comprehensive logging
- 🚀 **Production-Ready**: Optimized for deployment with zero downtime restarts

## 📋 Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message with auto quiz delivery |
| `/help` | Display help guide with all available commands |
| `/quiz` | Request a quiz question instantly |
| `/category` | Browse and select from 12 quiz categories |
| `/mystats` | View your real-time statistics (group + PM combined) |

### Developer Commands
| Command | Description |
|---------|-------------|
| `/dev` | Manage developer access (add/remove/list developers) |
| `/stats` | View real-time bot statistics dashboard |
| `/broadcast` | Send enhanced broadcast with media/buttons/placeholders |
| `/broadcast_confirm` | Confirm and send prepared enhanced broadcast |
| `/broadband` | Send simple plain text broadcast |
| `/broadband_confirm` | Confirm and send prepared plain text broadcast |
| `/delbroadcast` | Delete the latest broadcast message |
| `/delbroadcast_confirm` | Confirm deletion of latest broadcast |
| `/addquiz` | Add new quiz questions with duplicate detection |
| `/editquiz` | View and edit existing quiz questions (paginated) |
| `/delquiz` | Delete specific quiz question |
| `/delquiz_confirm` | Confirm quiz question deletion |
| `/totalquiz` | Display total count of available quiz questions |
| `/performance` | View live performance metrics dashboard |
| `/activity` | View live activity stream (with filtering/pagination) |
| `/clear_quizzes` | **DESTRUCTIVE** - Clear all quiz questions (double confirmation) |
| `/globalstats` | View comprehensive bot statistics (developer view) |
| `/allreload` | Restart bot globally without downtime |

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Git (for cloning)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd telegram-quiz-bot
```

2. **Install dependencies**

Using pip:
```bash
pip install -r requirements.txt
```

Or using uv (faster, recommended):
```bash
uv sync
```

3. **Set up environment variables**

Create a `.env` file or export these variables:
```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export SESSION_SECRET="your_random_secret_key_here"
```

4. **Configure developer access**

Edit `config.py` and add your Telegram user IDs:
```python
OWNER_ID = 123456789  # Your Telegram user ID (get from @userinfobot)
WIFU_ID = 987654321   # Secondary admin ID (optional)
```

5. **Run the bot**
```bash
python main.py
```

The bot will:
- Start the Telegram bot and Flask web server on port 5000
- Initialize the SQLite database with optimized indexes
- Load quiz questions from data/questions.json
- Start 7 automated background schedulers
- Begin accepting commands and polling for updates

## 📦 Dependencies

The project uses a minimal, optimized set of dependencies:

| Package | Purpose |
|---------|---------|
| **python-telegram-bot** | Telegram Bot API wrapper with job queue support |
| **flask** | Web framework for admin panel and health checks |
| **apscheduler** | Task scheduling for automated quiz delivery |
| **psutil** | System monitoring and memory tracking |
| **requests** | HTTP client for external API calls |
| **gunicorn** | Production WSGI server for deployment |

All dependencies are actively used and essential for core functionality. No bloat, no unused packages.

## 🌐 Admin Panel

Access the web-based admin panel at `http://localhost:5000` to:
- View all quiz questions in a responsive table
- Add new questions via web interface
- Edit existing questions with inline editing
- Delete questions with confirmation
- Monitor quiz statistics in real-time
- View active users and groups

## ⚙️ Configuration

### Quiz Categories
The bot supports 12 categories:
1. 🔬 Science
2. 📚 History
3. 🌍 Geography
4. ⚽ Sports
5. 💻 Technology
6. 🎬 Entertainment
7. 🎨 Art & Culture
8. 📖 Literature
9. 🏛️ Politics
10. 🍔 Food & Drink
11. 🎵 Music
12. 🔢 Mathematics

### Automated Schedulers
The bot runs 7 background jobs:
- **Automated Quiz Sender**: Every 30 minutes (sends quiz to active groups where bot is admin)
- **Scheduled Cleanup**: Hourly (removes inactive data)
- **Poll Cleanup**: Hourly (cleans up old poll data)
- **Question History Cleanup**: Daily (maintains quiz rotation freshness)
- **Memory Tracking**: Every 5 minutes (monitors performance)
- **Performance Metrics Cleanup**: Daily (removes metrics older than 7 days)
- **Activity Logs Cleanup**: Daily at 3 AM (keeps 30 days of audit trail)

### Network Resilience Settings
The bot includes robust network configuration:
- Connect timeout: 10 seconds
- Read timeout: 20 seconds
- Write timeout: 20 seconds
- Pool timeout: 10 seconds
- Connection pool size: 8
- Automatic reconnection on network failures

## 📁 Project Structure

```
telegram-quiz-bot/
├── main.py                 # Entry point - starts bot and Flask server
├── app.py                  # Flask application and bot initialization
├── bot_handlers.py         # Telegram command handlers and core logic
├── dev_commands.py         # Developer-only commands with access control
├── config.py               # Configuration, constants, and access control
├── database_manager.py     # SQLite database operations with optimized queries
├── quiz_manager.py         # Quiz business logic and data management
├── requirements.txt        # Python dependencies (auto-generated from pyproject.toml)
├── pyproject.toml          # Project metadata and dependency specifications
├── data/                   # Database and data files
│   ├── quiz_bot.db        # SQLite database (auto-created)
│   └── questions.json     # Quiz questions backup
├── static/                 # Static assets for web admin
│   └── js/
│       └── admin.js       # Admin panel JavaScript
└── templates/              # HTML templates for web admin
    └── admin.html         # Admin panel interface
```

## 🚀 Deployment

### Deploy on Replit (Recommended)
1. Import this repository to Replit
2. Add Secrets in Replit Tools → Secrets:
   - `TELEGRAM_TOKEN`: Your bot token
   - `SESSION_SECRET`: Random secret key
3. Update `config.py` with your `OWNER_ID`
4. Click Run - bot starts automatically!

### Deploy on Render
1. Create new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. Add Environment Variables in dashboard:
   - `TELEGRAM_TOKEN`
   - `SESSION_SECRET`
5. Deploy and your bot is live!

### Deploy on Heroku
1. Create new app on [Heroku](https://heroku.com)
2. Add Procfile to repository:
   ```
   web: python main.py
   ```
3. Set Config Vars (environment variables):
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token_here
   heroku config:set SESSION_SECRET=your_secret_here
   ```
4. Deploy:
   ```bash
   git push heroku main
   ```

## 🔧 Development

### Adding New Quiz Questions

**Via Bot (Recommended):**
```
/addquiz What is the capital of France?
London
Paris*
Berlin
Madrid

Category: Geography
```
*Mark correct answer with asterisk

**Via Admin Panel:**
1. Visit `http://localhost:5000`
2. Fill the web form with question details
3. Select category from dropdown
4. Mark the correct answer
5. Click "Add Question"

**Via JSON File:**
1. Edit `data/questions.json`
2. Add question object following the schema
3. Restart bot or use `/allreload`

### Developer Access Control
1. Set `OWNER_ID` in `config.py` (your Telegram user ID)
2. Owner can add developers: `/dev add @username`
3. Developers get full access to all admin commands
4. Remove developer access: `/dev remove @username`
5. List all developers: `/dev list`

### Database Schema
The bot uses SQLite with optimized indexes:

**Tables:**
- `questions` - Quiz questions with categories and answers
- `users` - User profiles, scores, and statistics
- `developers` - Developer access control and permissions
- `groups` - Registered groups for broadcasts and quizzes
- `user_daily_activity` - Daily activity tracking per user
- `quiz_history` - Complete quiz answer history
- `activity_logs` - Comprehensive audit trail with timestamps
- `performance_metrics` - Performance and health monitoring data
- `quiz_stats` - Aggregated quiz statistics
- `broadcast_logs` - Broadcast delivery tracking and analytics

**Optimized Indexes:**
- User ID lookups
- Chat ID queries
- Timestamp-based queries
- Category filtering
- Activity log searches

## 🐛 Troubleshooting

### Bot not responding
- ✅ Verify `TELEGRAM_TOKEN` is correct and valid
- ✅ Check bot is running: `python main.py`
- ✅ Review logs for errors: `tail -f bot.log`
- ✅ Ensure bot is not blocked by user/group

### Multiple Instance Conflict Error ⚠️
**Error:** `telegram.error.Conflict: terminated by other getUpdates request`

**Cause:** Multiple bot instances running simultaneously. Telegram API only allows ONE instance to poll for updates.

**How to identify:**
```bash
# Check for multiple instances
ps aux | grep "python main.py" | grep -v grep
# or
pgrep -a python
```

**How to fix:**
```bash
# Option 1: Kill all instances and restart
pkill -f "python main.py"
python main.py

# Option 2: Kill specific old instances (keep newest)
ps aux | grep "python main.py" | grep -v grep
kill <OLD_PID>  # Kill old instance, keep newest

# Option 3: Restart workflow in Replit
# Stop the workflow and start it again
```

**Prevention:**
- ⚠️ **NEVER run the bot in multiple terminals/tabs**
- ⚠️ **Close bot on local machine before running on server**
- ⚠️ **Use only ONE deployment method** (Replit OR Render OR Heroku, not multiple)
- ✅ Check for running instances before starting: `pgrep -a python`

### Network errors (httpx.ReadError)
- ✅ The bot has automatic reconnection built-in
- ✅ Network errors are logged but handled gracefully
- ✅ Bot will automatically retry with exponential backoff
- ✅ Check internet connection and Telegram API status

### Admin panel not accessible
- ✅ Ensure Flask is running on port 5000
- ✅ Check firewall/security group settings
- ✅ Verify `SESSION_SECRET` environment variable is set
- ✅ Try accessing `http://127.0.0.1:5000` instead

### Quiz not sending automatically
- ✅ Bot must be admin in groups for auto-quiz to work
- ✅ Grant "Delete messages" permission for auto-cleanup
- ✅ Check scheduler logs in console output
- ✅ Verify groups are registered: `/stats` command
- ✅ Ensure quiz questions exist: `/totalquiz`

### Auto-cleanup not working
- ✅ Bot needs admin status with "Delete messages" permission
- ✅ Auto-cleanup only works in groups (not PMs)
- ✅ Check bot permissions in group settings
- ✅ Review logs for deletion errors

## 📊 Performance Monitoring

The bot includes comprehensive performance tracking:

**Metrics Tracked:**
- Memory usage (every 5 minutes)
- API call counts and response times
- Error rates and types
- User activity patterns
- Quiz delivery success rates
- Broadcast delivery analytics

**View Metrics:**
- Use `/performance [hours]` command (developer only)
- Customize time window: `/performance 24` for last 24 hours
- Export metrics from database: `activity_logs` and `performance_metrics` tables

**Health Monitoring:**
- Memory tracking prevents memory leaks
- Automatic cleanup of old metrics (7-day retention)
- Performance degradation alerts in logs
- System resource monitoring with psutil

## 🔒 Security Features

- ✅ **Role-based access control** for developer commands
- ✅ **Unauthorized access attempt logging** with user tracking
- ✅ **Session-based admin panel authentication** with Flask sessions
- ✅ **Environment variable protection** for sensitive data (tokens, secrets)
- ✅ **SQL injection prevention** via parameterized queries
- ✅ **Auto-cleanup of unauthorized messages** in groups
- ✅ **Developer command response preservation** (never auto-cleaned)
- ✅ **Beautiful unauthorized access messages** with decorative design
- ✅ **Comprehensive audit trail** in activity_logs table

## 🧪 Testing

### Manual Testing Checklist
- [ ] Bot responds to `/start` in PM
- [ ] Bot responds to `/start` in group
- [ ] Auto-quiz delivers after 5s in PM
- [ ] Auto-quiz delivers every 30min in groups (where bot is admin)
- [ ] Quiz answers tracked correctly
- [ ] `/mystats` shows real-time statistics
- [ ] `/category` displays all 12 categories
- [ ] Developer commands require authorization
- [ ] Broadcast system works with placeholders
- [ ] Auto-cleanup removes old messages in groups
- [ ] Admin panel accessible and functional
- [ ] Network resilience handles disconnections

### Code Quality Tools

This project follows PEP8 and uses automated formatting:

**Format code with Black:**
```bash
black .
```

**Sort imports with isort:**
```bash
isort .
```

**Lint code with flake8:**
```bash
flake8 .
```

**Run all checks:**
```bash
black . && isort . && flake8 .
```

**Install dev dependencies:**
```bash
pip install -e ".[dev]"
```

## 📝 Maintenance

### Backup Database
```bash
# Create backup
cp data/quiz_bot.db data/backup_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp data/backup_20250103_120000.db data/quiz_bot.db
```

### View Live Logs
```bash
# Follow bot logs in real-time
tail -f bot.log

# Filter for errors only
grep ERROR bot.log

# View last 100 lines
tail -100 bot.log
```

### Database Management
```bash
# Open SQLite database
sqlite3 data/quiz_bot.db

# Export questions to JSON
# (automatically done on shutdown)

# View table structure
sqlite3 data/quiz_bot.db ".schema"
```

## 🤝 Contributing

Contributions are welcome! Please:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Follow code style**: Use Black, isort, flake8
4. **Test thoroughly**: Both PM and group chats
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open Pull Request** with detailed description

### Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/telegram-quiz-bot.git
cd telegram-quiz-bot

# Install dependencies
pip install -r requirements.txt

# Install dev tools
pip install -e ".[dev]"

# Run the bot
python main.py
```

## 📧 Support

For issues, questions, or suggestions:
- 🐛 **Bug Reports**: Open an issue on GitHub with detailed steps to reproduce
- 💡 **Feature Requests**: Open an issue with "[Feature]" prefix
- 📖 **Documentation**: Check `replit.md` for technical details
- 💬 **Community**: Contact bot owner via Telegram

## 📝 License

This project is open source and available under the **MIT License**.

## 🎉 Acknowledgments

Built with ❤️ using these amazing technologies:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Flask](https://flask.palletsprojects.com/) - Web framework for admin panel
- [APScheduler](https://apscheduler.readthedocs.io/) - Background job scheduling
- [SQLite](https://www.sqlite.org/) - Embedded database engine

Special thanks to the open-source community for these incredible tools!

---

**Made with ❤️ by the Telegram Quiz Bot Team**

**Ready to deploy?** Follow the deployment guide above and your quiz bot will be live in minutes! 🚀
