# 🎯 Telegram Quiz Bot

A production-ready Telegram Quiz Bot with automated quiz delivery, live real-time statistics tracking, category-based filtering, and comprehensive analytics. Built with Python, Flask, and python-telegram-bot.

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
- 📢 **Broadcast System**: Send announcements with media, buttons, and placeholders
- 🧹 **Auto-Cleanup**: Automatically removes old quiz messages for clean chat experience

### Technical Features
- 💾 **SQLite Database**: Efficient data storage with optimized indexes
- 🔄 **Background Jobs**: 7 automated schedulers for cleanup and monitoring
- 📝 **Activity Logging**: Complete audit trail of all bot interactions
- 🛡️ **Error Handling**: Robust error recovery and logging
- 🚀 **Production-Ready**: Optimized for deployment on Render, Heroku, or Replit

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
| `/dev` | Access developer control panel |
| `/stats` | View bot-wide statistics and analytics |
| `/broadcast` | Send announcements to all users/groups |
| `/delbroadcast` | Delete previous broadcasts |
| `/addquiz` | Add new quiz questions |
| `/editquiz` | Edit existing questions |
| `/delquiz` | Delete quiz questions |
| `/totalquiz` | View all quiz questions |

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

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
   
   Or install from pyproject.toml directly:
   ```bash
   pip install .
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
   OWNER_ID = 123456789  # Your Telegram user ID
   WIFU_ID = 987654321   # Secondary admin ID (optional)
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

The bot will:
- Start the Telegram bot and web server
- Initialize the SQLite database
- Load quiz questions
- Start 7 automated background jobs
- Begin accepting commands

## 📦 Dependencies

The project uses a minimal set of essential dependencies:

| Package | Purpose | Why Required |
|---------|---------|--------------|
| **python-telegram-bot** | Telegram Bot API | Core bot functionality |
| **flask** | Web framework | Admin panel and health checks |
| **flask-sqlalchemy** | ORM | APScheduler job persistence |
| **apscheduler** | Task scheduling | Automated quiz delivery |
| **psycopg2-binary** | PostgreSQL adapter | Production database support |
| **psutil** | System monitoring | Memory tracking and health checks |
| **requests** | HTTP client | Keep-alive pings |
| **gunicorn** | WSGI server | Production deployment |

### Why These Dependencies?
- **flask-sqlalchemy**: Required by APScheduler for persistent job storage (scheduler won't work without it)
- **psycopg2-binary**: Enables PostgreSQL support for production deployments (falls back to SQLite if not available)
- All other dependencies are directly imported and actively used in the codebase

## 🌐 Deployment

### Deploy to Render

1. **Create a new Web Service** on [Render](https://render.com)

2. **Configure the service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`
   - **Environment Variables**:
     - `TELEGRAM_TOKEN`: Your bot token
     - `SESSION_SECRET`: Random secret key

3. **Deploy** and your bot will be live!

### Deploy to Heroku

1. **Create a new app** on [Heroku](https://heroku.com)

2. **Add Procfile**:
   ```
   web: gunicorn --bind=0.0.0.0:$PORT --reuse-port main:app
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token_here
   heroku config:set SESSION_SECRET=your_secret_here
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

### Deploy to Replit

1. **Import the repository** to Replit

2. **Set Secrets**:
   - Go to Tools → Secrets
   - Add `TELEGRAM_TOKEN` and `SESSION_SECRET`

3. **Configure the Run button**:
   - Command: `python main.py`
   - Port: 5000

4. **Click Run** and your bot is live!

## 📁 Project Structure

```
telegram-quiz-bot/
├── main.py                 # Application entry point
├── app.py                  # Flask web application
├── bot_handlers.py         # Telegram bot command handlers
├── dev_commands.py         # Developer commands module
├── quiz_manager.py         # Quiz logic and data management
├── database_manager.py     # SQLite database operations
├── config.py              # Configuration and access control
├── keep_alive.py          # Keep-alive server and health checks
├── templates/             # Flask HTML templates
│   └── admin.html        # Admin panel interface
├── static/               # Static assets
│   └── js/
│       └── admin.js      # Admin panel JavaScript
├── data/                 # Data directory
│   ├── quiz_bot.db      # SQLite database
│   ├── questions.json   # Quiz questions backup
│   └── *.json           # Other data files
└── pyproject.toml        # Python dependencies
```

## 🛠️ Configuration

### Access Control
Edit `config.py` to manage developer access:

```python
OWNER_ID = 123456789      # Primary admin
WIFU_ID = 987654321       # Secondary admin
```

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

### Background Jobs
The bot runs 7 automated schedulers:
- **Auto Quiz Sender**: Every 30 minutes
- **Scheduled Cleanup**: Hourly
- **Poll Cleanup**: Hourly  
- **Question History Cleanup**: Hourly
- **Memory Tracking**: Every 5 minutes
- **Performance Metrics Cleanup**: Daily
- **Activity Logs Cleanup**: Daily at 3 AM

## 🔧 Maintenance

### View Logs
```bash
tail -f bot.log
```

### Backup Database
```bash
cp data/quiz_bot.db data/quiz_bot_backup.db
```

### Add Quiz Questions
Use the `/addquiz` developer command or manually edit `data/questions.json`

### Monitor Performance
- Admin panel: `http://localhost:5000`
- Health check: `http://localhost:5000/health`
- Use `/stats` command for bot analytics

## 📊 Database Schema

The bot uses SQLite with the following tables:
- **questions**: Quiz questions with categories
- **users**: User profiles and statistics
- **developers**: Developer access control
- **groups**: Group chat information
- **quiz_history**: Quiz attempt tracking
- **activity_logs**: Complete activity audit trail
- **performance_metrics**: Performance analytics
- **broadcast_logs**: Broadcast history

## 🤝 Support & Contribution

### Getting Help
- Check the `/help` command in the bot
- Review the code documentation in `replit.md`
- Open an issue on GitHub

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is open source and available under the MIT License.

## 🎉 Credits

Built with ❤️ using:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Flask](https://flask.palletsprojects.com/)
- [APScheduler](https://apscheduler.readthedocs.io/)

---

**Ready to deploy?** Follow the deployment guide above and your quiz bot will be live in minutes! 🚀
