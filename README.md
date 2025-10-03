# 🎯 Telegram Quiz Bot

A production-ready Telegram quiz bot with automated scheduling, user statistics, admin panel, and universal deployment support. Works seamlessly on Replit, Render, Railway, Heroku, VPS, Docker, and more!

## 📋 Overview

Telegram Quiz Bot is a feature-rich bot that delivers interactive quizzes to users and groups. It supports automated quiz scheduling, comprehensive statistics tracking, and includes a web-based admin panel for easy quiz management. The bot intelligently auto-detects deployment mode (polling vs webhook) for maximum compatibility across platforms.

## ✨ Features

- 🎲 **Interactive Quiz System** - Multiple choice questions with instant results and scoring
- ⏰ **Automated Quiz Scheduling** - Automatic quiz delivery every 30 minutes to active groups
- 📊 **User Statistics & Leaderboards** - Track performance, rankings, and quiz history
- 🎨 **Admin Panel** - Flask-based web interface for quiz management (add/edit/delete questions)
- 👨‍💻 **Developer Commands** - Advanced commands for bot administration and analytics
- 📢 **Broadcast System** - Send announcements to all users or groups with inline button support
- 🔄 **Dual Mode Support** - Auto-detection of webhook or polling mode based on environment
- 🧹 **Smart Auto-Cleanup** - Automatically removes old quiz messages in groups
- 🗄️ **SQLite Database** - Persistent storage for questions, users, groups, and statistics
- 🌍 **Universal Deployment** - Works on any platform without code modifications

## 🛠️ Tech Stack

- **Bot Framework:** python-telegram-bot 21.0
- **Web Framework:** Flask 3.0.0
- **Database:** SQLite
- **Web Server:** Gunicorn 21.2.0
- **Task Scheduler:** APScheduler
- **Additional:** python-dotenv, httpx, psutil

## 🚀 Quick Start

### Prerequisites

1. **Telegram Bot Token** - Create a bot with [@BotFather](https://t.me/BotFather)
2. **Session Secret** - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
3. **Your Telegram User ID** - Get from [@userinfobot](https://t.me/userinfobot)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-quiz-bot.git
   cd telegram-quiz-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

5. **Access admin panel** (optional)
   - Open browser: `http://localhost:5000/admin`

## 🔧 Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_TOKEN` | ✅ Yes | Your bot token from @BotFather | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `SESSION_SECRET` | ✅ Yes | Secret key for Flask sessions | `a1b2c3d4e5f6...` (64 chars) |
| `OWNER_ID` | ⚠️ Recommended | Your Telegram user ID (enables admin features) | `123456789` |
| `WEBHOOK_URL` | ❌ Optional | Full webhook URL for webhook mode | `https://yourapp.com/webhook` |
| `RENDER_URL` | ❌ Optional | Render-specific webhook URL | `https://yourapp.onrender.com/webhook` |
| `PORT` | ❌ Optional | Web server port (default: 5000) | `5000` |

**Additional Variables:**
- `WIFU_ID` - Secondary admin user ID (optional)
- `DATABASE_PATH` - Custom database path (default: `data/quiz_bot.db`)

## 🤖 Mode Detection

The bot automatically detects which mode to run based on environment variables:

### Polling Mode (Default)
- **When:** No `WEBHOOK_URL` or `RENDER_URL` is set
- **Platforms:** Replit, VPS, local development
- **Behavior:** Bot actively polls Telegram servers for updates
- **Advantages:** Works anywhere, no public URL required

### Webhook Mode
- **When:** `WEBHOOK_URL` or `RENDER_URL` is set
- **Platforms:** Render, Railway, Heroku, cloud hosting
- **Behavior:** Telegram sends updates to your webhook URL
- **Advantages:** More efficient for high-traffic bots

**The bot handles everything automatically** - just set the appropriate environment variables!

## 📦 Deployment Guides

### 🟦 Replit (Easiest)

1. **Import Repository**
   - Fork this Repl or import from GitHub

2. **Configure Secrets**
   - Open "Secrets" tab (🔒 icon)
   - Add required variables:
     - `TELEGRAM_TOKEN`
     - `SESSION_SECRET`
     - `OWNER_ID`

3. **Run**
   - Click the "Run" button
   - Bot starts automatically in polling mode ✅

4. **Access Admin Panel**
   - Click the webview URL
   - Navigate to `/admin`

**Mode:** Polling (automatic)

---

### 🟩 Railway

1. **Create New Project**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Set Environment Variables**
   ```
   TELEGRAM_TOKEN=your_token_here
   SESSION_SECRET=your_secret_here
   OWNER_ID=your_user_id
   ```

3. **Deploy**
   - Railway auto-detects Python and runs `python main.py`
   - Bot starts in polling mode automatically

**Mode:** Polling (default)  
**Free Tier:** $5 credit/month

---

### 🟪 Render

1. **Create Web Service**
   - Go to [Render.com](https://render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Build**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn src.web.wsgi:app --bind 0.0.0.0:$PORT`

3. **Set Environment Variables**
   ```
   TELEGRAM_TOKEN=your_token_here
   SESSION_SECRET=your_secret_here
   OWNER_ID=your_user_id
   RENDER_URL=https://your-app-name.onrender.com/webhook
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Bot automatically switches to webhook mode

**Mode:** Webhook (auto-detected from `RENDER_URL`)  
**Free Tier:** 750 hours/month

---

### 🟥 Heroku

1. **Install Heroku CLI**
   ```bash
   # Install from https://devcenter.heroku.com/articles/heroku-cli
   heroku login
   ```

2. **Create Heroku App**
   ```bash
   heroku create your-quiz-bot
   ```

3. **Set Config Vars**
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token
   heroku config:set SESSION_SECRET=your_secret
   heroku config:set OWNER_ID=your_user_id
   heroku config:set WEBHOOK_URL=https://your-quiz-bot.herokuapp.com/webhook
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Check Status**
   ```bash
   heroku logs --tail
   ```

**Mode:** Webhook (auto-detected from `WEBHOOK_URL`)  
**Note:** Uses Procfile automatically

---

### 🐳 Docker

**Option 1: Docker CLI**

1. **Build Image**
   ```bash
   docker build -t telegram-quiz-bot .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     -e TELEGRAM_TOKEN=your_token \
     -e SESSION_SECRET=your_secret \
     -e OWNER_ID=your_user_id \
     -p 5000:5000 \
     --name quiz-bot \
     telegram-quiz-bot
   ```

**Option 2: Docker Compose**

1. **Create `.env` file**
   ```env
   TELEGRAM_TOKEN=your_token
   SESSION_SECRET=your_secret
   OWNER_ID=your_user_id
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **View Logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop Services**
   ```bash
   docker-compose down
   ```

**Mode:** Polling (default) - webhook available if `WEBHOOK_URL` is set

---

### 🖥️ VPS / Linux Server

1. **SSH into Server**
   ```bash
   ssh user@your-server-ip
   ```

2. **Install Python 3.11+**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv -y
   ```

3. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/telegram-quiz-bot.git
   cd telegram-quiz-bot
   ```

4. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure Environment**
   ```bash
   nano .env
   # Add your environment variables
   ```

7. **Run Bot**
   
   **Polling Mode (Recommended):**
   ```bash
   python main.py
   ```
   
   **Webhook Mode:**
   ```bash
   gunicorn src.web.wsgi:app --bind 0.0.0.0:5000
   ```

8. **Keep Running (Optional - using screen)**
   ```bash
   screen -S telegram-bot
   python main.py
   # Press Ctrl+A then D to detach
   ```

   **Or use systemd service:**
   ```bash
   sudo nano /etc/systemd/system/telegram-quiz-bot.service
   ```
   
   ```ini
   [Unit]
   Description=Telegram Quiz Bot
   After=network.target

   [Service]
   Type=simple
   User=your-username
   WorkingDirectory=/path/to/telegram-quiz-bot
   ExecStart=/path/to/telegram-quiz-bot/venv/bin/python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   sudo systemctl enable telegram-quiz-bot
   sudo systemctl start telegram-quiz-bot
   ```

**Mode:** Polling (default)

---

## 📁 Project Structure

```
telegram-quiz-bot/
├── src/
│   ├── bot/                    # Telegram bot components
│   │   ├── handlers.py         # Command handlers & schedulers
│   │   └── dev_commands.py     # Developer commands
│   ├── core/                   # Core business logic
│   │   ├── config.py           # Configuration & mode detection
│   │   ├── database.py         # SQLite database operations
│   │   └── quiz.py             # Quiz management logic
│   └── web/                    # Flask web application
│       ├── app.py              # Web server & API endpoints
│       └── wsgi.py             # WSGI entry point
├── templates/                  # HTML templates
│   └── admin.html              # Admin panel interface
├── static/                     # Static files
│   └── js/
│       └── admin.js            # Admin panel JavaScript
├── data/                       # Database & persistent data
│   ├── quiz_bot.db             # SQLite database (auto-created)
│   ├── questions.json          # Quiz questions backup
│   └── *.json                  # Other data files
├── main.py                     # Universal entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Heroku/Render config
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Docker Compose config
├── .env.example                # Environment template
└── README.md                   # This file
```

## 🎮 Bot Commands

### User Commands
- `/start` - Begin your quiz journey
- `/help` - View all available commands
- `/quiz` - Get a random quiz question
- `/category` - Browse quiz categories
- `/mystats` - View your statistics
- `/leaderboard` - See top performers
- `/ping` - Check bot responsiveness

### Admin Commands (Owner Only)
- `/addquiz` - Add new quiz questions
- `/editquiz` - Edit existing quizzes
- `/delquiz` - Delete quiz questions
- `/broadcast` - Send messages to all users
- `/stats` - View bot statistics
- `/devstats` - Developer analytics
- `/cleanup` - Clean inactive chats
- `/restart` - Restart the bot

## 🔌 Admin Panel Features

Access the web admin panel at `/admin`:

- **Question Management**
  - Add new quiz questions
  - Edit existing questions
  - Delete questions
  - View all questions

- **REST API Endpoints**
  - `GET /api/questions` - List all questions
  - `POST /api/questions` - Add question
  - `PUT /api/questions/<id>` - Update question
  - `DELETE /api/questions/<id>` - Delete question

## 🛡️ Security Best Practices

- Never commit `.env` file (already in `.gitignore`)
- Never share your `TELEGRAM_TOKEN` publicly
- Regenerate `SESSION_SECRET` for each deployment
- Use environment variables on cloud platforms (not `.env` files)
- Keep `OWNER_ID` private to prevent unauthorized access
- Regularly update dependencies: `pip install -r requirements.txt --upgrade`

## 🗄️ Database

The bot uses **SQLite** for data persistence:

- **Location:** `data/quiz_bot.db` (auto-created on first run)
- **Tables:** 
  - `questions` - Quiz questions and answers
  - `users` - User profiles and settings
  - `groups` - Group chat information
  - `statistics` - Quiz performance data
  - `activity_logs` - Command and event logs
- **Automatic Backups:** Created on startup
- **No Setup Required:** Database initializes automatically

## 🐛 Troubleshooting

### Bot Not Responding

1. **Check Logs**
   - Replit: Console tab
   - Heroku: `heroku logs --tail`
   - Docker: `docker logs quiz-bot`
   - VPS: `tail -f bot.log`

2. **Verify Environment Variables**
   - Ensure `TELEGRAM_TOKEN` is correct
   - Confirm `SESSION_SECRET` is set
   - Check `OWNER_ID` is valid

3. **Test Bot Token**
   - Send `/start` to your bot on Telegram
   - Check if @BotFather shows bot as active

4. **Check Bot Mode**
   - Look for "Starting in POLLING mode" or "Starting in WEBHOOK mode" in logs
   - Ensure mode matches your deployment platform

### Webhook Mode Issues (Render/Heroku/Railway)

1. **Verify Webhook URL**
   - Must be `https://` (not `http://`)
   - Must end with `/webhook`
   - Example: `https://yourapp.onrender.com/webhook`

2. **Check Start Command**
   - Should be: `gunicorn src.web.wsgi:app --bind 0.0.0.0:$PORT`
   - Verify Procfile is correct

3. **Test Health Endpoint**
   - Visit: `https://yourapp.com/`
   - Should return: `{"status":"ok"}`

4. **Check Webhook Status**
   - Use Telegram API: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Polling Mode Issues (Replit/VPS)

1. **Check for Multiple Instances**
   - Only one bot can poll at a time
   - Kill other instances: `pkill -f "python main.py"`

2. **Verify Internet Connection**
   - Test: `ping telegram.org`

3. **Check Telegram API Status**
   - Visit: [Telegram Status](https://t.me/BotNews)

### Database Issues

1. **Database Locked**
   - Stop all bot instances
   - Check file permissions: `chmod 644 data/quiz_bot.db`

2. **Questions Not Showing**
   - Verify `data/questions.json` exists
   - Check logs for database initialization errors

3. **Reset Database**
   ```bash
   rm data/quiz_bot.db
   python main.py  # Auto-recreates database
   ```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/telegram-quiz-bot.git
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Your Changes**
   - Follow existing code style
   - Add comments for complex logic
   - Test thoroughly

4. **Commit Your Changes**
   ```bash
   git commit -m "Add amazing feature"
   ```

5. **Push to Branch**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Describe your changes
   - Reference any related issues

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Add docstrings to new functions
- Update README if adding new features
- Test on multiple platforms when possible

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with these amazing open-source projects:

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Advanced Python Scheduler
- [Gunicorn](https://gunicorn.org/) - Python WSGI HTTP Server
- [SQLite](https://www.sqlite.org/) - Self-contained SQL database

## 💬 Support

Need help? Here's how to get support:

1. **Check Documentation**
   - Read this README thoroughly
   - Review troubleshooting section

2. **Check Logs**
   - Platform-specific log locations above
   - Look for error messages

3. **Open an Issue**
   - [GitHub Issues](https://github.com/yourusername/telegram-quiz-bot/issues)
   - Provide logs and configuration details

4. **Community**
   - Ask questions in Discussions
   - Share your deployment experiences

## 🌟 Star History

If this project helped you, please consider giving it a ⭐️ on GitHub!

---

**Made with ❤️ for the Telegram community**

*Deploy once, run anywhere! 🚀*
