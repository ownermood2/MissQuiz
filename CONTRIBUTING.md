# Contributing to Telegram Quiz Bot

Thank you for your interest in contributing to the Telegram Quiz Bot project! We welcome contributions from the community.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/telegram-quiz-bot.git
   cd telegram-quiz-bot
   ```
3. **Create a new branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install development tools** (for code formatting):
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your TELEGRAM_TOKEN and SESSION_SECRET
   ```

4. **Run the bot** to test your changes:
   ```bash
   python main.py
   ```

## 📝 Code Style & Quality

We use automated tools to maintain consistent code quality:

### Code Formatting

Before submitting a pull request, format your code with Black:
```bash
black .
```

### Import Sorting

Sort your imports with isort:
```bash
isort .
```

### Linting

Check your code with flake8:
```bash
flake8 .
```

### Run All Checks at Once

```bash
black . && isort . && flake8 .
```

## 🧪 Testing Your Changes

1. **Test locally** - Run the bot and verify all commands work
2. **Check the admin panel** - Visit `http://localhost:5000` and test the web interface
3. **Test in both PM and groups** - Ensure commands work in different chat types
4. **Verify background jobs** - Check that scheduled tasks execute correctly
5. **Review logs** - Check `bot.log` for any errors or warnings

## 📋 Pull Request Process

1. **Ensure your code follows our style guidelines** (Black, isort, flake8)
2. **Test thoroughly** - Make sure all features work as expected
3. **Update documentation** if you're adding new features
4. **Write clear commit messages**:
   ```
   feat: Add user leaderboard command
   fix: Resolve broadcast deletion error
   docs: Update deployment guide for Railway
   ```
5. **Submit your pull request** with a clear description of changes

## 🐛 Reporting Bugs

When reporting bugs, please include:
- **Description** - What happened vs. what you expected
- **Steps to reproduce** - How can we recreate the issue?
- **Environment** - Python version, OS, deployment platform
- **Logs** - Relevant error messages from `bot.log`

## 💡 Suggesting Features

We welcome feature suggestions! Please:
- **Check existing issues** to avoid duplicates
- **Describe the use case** - Why is this feature needed?
- **Explain the implementation** - How should it work?
- **Consider alternatives** - Are there other ways to solve the problem?

## 📂 Project Structure

Understanding the codebase:

```
telegram-quiz-bot/
├── main.py              # Entry point and bot lifecycle
├── app.py               # Flask web application
├── bot_handlers.py      # User command handlers
├── dev_commands.py      # Developer/admin commands
├── quiz_manager.py      # Quiz logic and scoring
├── database_manager.py  # Database operations
└── config.py           # Configuration and access control
```

## 🔑 Key Areas for Contribution

- **New quiz categories** - Add more question types and topics
- **Command improvements** - Enhance user experience and functionality
- **Performance optimizations** - Improve response times and efficiency
- **Documentation** - Expand guides, add examples, fix typos
- **Bug fixes** - Resolve issues and edge cases
- **Deployment guides** - Add support for new platforms

## ⚠️ Important Notes

- **Never commit secrets** - Keep `.env` in `.gitignore`
- **Test with real Telegram** - Use a test bot token for development
- **Respect user privacy** - Don't log sensitive user data
- **Follow async patterns** - Use `async/await` for Telegram API calls
- **Handle errors gracefully** - Add try/except blocks with proper logging

## 📞 Getting Help

- **Open an issue** - Ask questions or report problems
- **Join discussions** - Participate in GitHub Discussions (if enabled)
- **Check the documentation** - Review README.md and code comments

## 📜 Code of Conduct

- **Be respectful** - Treat all contributors with kindness
- **Be constructive** - Provide helpful, actionable feedback
- **Be collaborative** - Work together to improve the project
- **Be patient** - Everyone is learning and contributing in their own way

## ✨ Recognition

All contributors will be recognized in our project documentation. Thank you for helping make Telegram Quiz Bot better!

---

**Ready to contribute?** Fork the repo, make your changes, and submit a pull request. We're excited to see what you build! 🚀
