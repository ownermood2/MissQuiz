# 🎯 Telegram Quiz Bot - Universal Deployment

A production-ready Telegram Quiz Bot that works **anywhere** - Replit, Render, Railway, VPS, Heroku, or Docker. Drop it on any platform and it runs instantly! 🚀

---

## ✨ Features

- 🎲 **Interactive Quizzes** - Multiple choice questions with instant results
- 🕒 **Auto-Scheduled Quizzes** - Automatic quiz delivery every 30 minutes
- 📊 **Statistics & Leaderboards** - Track user performance and rankings
- 👥 **Group Support** - Works in both private chats and groups
- 🧹 **Auto-Cleanup** - Automatically deletes old quiz messages in groups
- 📱 **Universal Deployment** - Works on any platform without code changes
- 🔄 **Smart Mode Detection** - Auto-switches between webhook and polling modes

---

## 🚀 Quick Start

### Prerequisites

1. **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
2. **Session Secret** - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
3. **Your Telegram User ID** (optional) - Get from [@userinfobot](https://t.me/userinfobot)

### Environment Variables

Create a `.env` file (or set in your platform):

```env
TELEGRAM_TOKEN=your_bot_token_here
SESSION_SECRET=your_generated_secret_here
OWNER_ID=your_telegram_user_id

# For webhook mode (Render/Railway/Heroku):
RENDER_URL=https://your-app.onrender.com/webhook
```

---

## 📦 Deployment Guides

### 🔵 **Replit** (Easiest - Recommended for Beginners)

1. **Fork this Repl** or import from GitHub
2. **Add Secrets** in the "Secrets" tab:
   - `TELEGRAM_TOKEN` = your bot token
   - `SESSION_SECRET` = your session secret
   - `OWNER_ID` = your Telegram user ID (optional)
3. **Click Run** - Bot starts automatically in polling mode!

**That's it!** Your bot is live. The workflow auto-starts on run.

---

### 🟢 **Railway** (Best for Always-On)

1. **Sign up** at [Railway.app](https://railway.app)
2. **New Project** → Deploy from GitHub repo
3. **Add Environment Variables**:
   - `TELEGRAM_TOKEN`
   - `SESSION_SECRET`
   - `OWNER_ID` (optional)
4. **Deploy** - Railway auto-detects `python main.py` and runs it

**Mode:** Polling (default) - No webhook configuration needed!

**Free Tier:** $5 credit/month, sufficient for small to medium bots

---

### 🟣 **Render** (Webhook Mode)

1. **Sign up** at [Render.com](https://render.com)
2. **New Web Service** → Connect your GitHub repo
3. **Configure**:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn main:app --workers=1 --bind=0.0.0.0:$PORT`
4. **Add Environment Variables**:
   - `TELEGRAM_TOKEN`
   - `SESSION_SECRET`
   - `RENDER_URL` = `https://your-app.onrender.com/webhook`
   - `OWNER_ID` (optional)
5. **Deploy** - Bot auto-switches to webhook mode!

**Mode:** Webhook (auto-detected from RENDER_URL)

**Free Tier:** Available with 750 hours/month

---

### 🔴 **Heroku** (Classic Cloud Platform)

1. **Install** [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. **Login:** `heroku login`
3. **Create App:** `heroku create your-bot-name`
4. **Add Config Vars:**
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token
   heroku config:set SESSION_SECRET=your_secret
   heroku config:set WEBHOOK_URL=https://your-bot-name.herokuapp.com/webhook
   heroku config:set OWNER_ID=your_user_id
   ```
5. **Deploy:**
   ```bash
   git push heroku main
   ```

**Mode:** Webhook (auto-detected from WEBHOOK_URL)

---

### 🖥️ **VPS** (DigitalOcean, AWS, Linode, etc.)

1. **SSH into your server**
2. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/telegram-quiz-bot.git
   cd telegram-quiz-bot
   ```
3. **Install Python 3.11+:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```
4. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
6. **Create .env file:**
   ```bash
   nano .env
   # Add your environment variables
   ```
7. **Run the bot:**
   ```bash
   python main.py
   ```
8. **Keep it running (optional - using screen):**
   ```bash
   screen -S telegram-bot
   python main.py
   # Press Ctrl+A then D to detach
   ```

**Mode:** Polling (default) - No webhook setup needed!

---

### 🐳 **Docker**

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   CMD ["python", "main.py"]
   ```

2. **Build:**
   ```bash
   docker build -t telegram-quiz-bot .
   ```

3. **Run:**
   ```bash
   docker run -d \
     -e TELEGRAM_TOKEN=your_token \
     -e SESSION_SECRET=your_secret \
     -e OWNER_ID=your_user_id \
     --name quiz-bot \
     telegram-quiz-bot
   ```

**Mode:** Polling (default)

---

## 🛠️ Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/telegram-quiz-bot.git
   cd telegram-quiz-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

The bot will automatically detect your environment and run in polling mode.

---

## 📁 Project Structure

```
telegram-quiz-bot/
├── src/
│   ├── core/              # Core business logic
│   │   ├── config.py      # Configuration & environment detection
│   │   ├── database.py    # SQLite database operations
│   │   └── quiz.py        # Quiz management logic
│   ├── bot/               # Telegram bot components
│   │   ├── handlers.py    # Bot command handlers & schedulers
│   │   └── dev_commands.py # Developer-specific commands
│   └── web/               # Flask web application
│       └── app.py         # Web server, API, webhook support
├── data/                  # Database & persistent data
│   └── quiz_bot.db        # SQLite database (auto-created)
├── main.py                # Universal entry point
├── requirements.txt       # Python dependencies
├── Procfile               # Render/Heroku deployment config
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

---

## 🎮 Bot Commands

### User Commands
- `/start` - Begin your quiz journey
- `/help` - View all commands
- `/quiz` - Get a random quiz question
- `/category` - Explore quiz categories
- `/mystats` - Check your performance
- `/leaderboard` - View top performers
- `/ping` - Test bot responsiveness

### Admin Commands (Owner Only)
- `/addquiz` - Add new quiz questions
- `/broadcast` - Send messages to all users
- `/stats` - View bot statistics
- `/devstats` - Developer statistics
- `/cleanup` - Clean inactive chats

---

## 🔧 How It Works

### Universal Mode Detection

The bot automatically detects which mode to run based on environment variables:

**Webhook Mode** (Render/Railway/Heroku):
- Detects if `RENDER_URL` or `WEBHOOK_URL` is set
- Runs Flask app with gunicorn
- Receives updates via HTTP webhook
- Best for cloud platforms with public URLs

**Polling Mode** (Replit/VPS/Local):
- Default mode when no webhook URL is set
- Actively polls Telegram servers for updates
- Works anywhere without public URL
- Perfect for development and VPS

### Single Command

```bash
python main.py
```

That's all you need! The bot handles the rest:
1. Loads configuration from `.env` or environment
2. Detects deployment mode (webhook vs polling)
3. Initializes database
4. Starts appropriate server
5. Begins processing Telegram updates

---

## 🔐 Security Notes

- Never commit `.env` file to Git (already in `.gitignore`)
- Never share your `TELEGRAM_TOKEN` publicly
- Regenerate `SESSION_SECRET` for production deployments
- Use environment variables on cloud platforms (not `.env` files)

---

## 📊 Database

The bot uses **SQLite** for data persistence:
- **Location:** `data/quiz_bot.db` (auto-created)
- **Tables:** questions, users, groups, stats, activity logs
- **Automatic backups:** On startup
- **No setup required:** Database initializes automatically

---

## 🐛 Troubleshooting

### Bot Not Responding

1. **Check logs** on your platform
2. **Verify environment variables** are set correctly
3. **Ensure TELEGRAM_TOKEN is valid** (test with @BotFather)
4. **Check bot mode:** Look for "Starting in POLLING mode" or "Starting in WEBHOOK mode" in logs

### Webhook Mode Issues (Render/Heroku)

1. **Verify RENDER_URL/WEBHOOK_URL** is correct (must end with `/webhook`)
2. **Check Start Command:** Should be `gunicorn main:app --workers=1 --bind=0.0.0.0:$PORT`
3. **View logs** for webhook errors
4. **Test health endpoint:** Visit `https://your-app.com/` - should return `{"status":"ok"}`

### Polling Mode Issues (Replit/VPS)

1. **Check if another instance is running** (only one bot can poll at a time)
2. **Verify internet connection**
3. **Check Telegram API status** at [Telegram Status](https://t.me/BotNews)

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

## 📄 License

This project is open source. Feel free to use, modify, and distribute as needed.

---

## 💡 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs on your deployment platform
3. Open an issue on GitHub

---

## 🎉 Credits

Built with:
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- [SQLite](https://www.sqlite.org/) - Database

---

**Made with ❤️ for the Telegram community**

---

*Now go deploy your bot and let the quiz fun begin! 🎯*
