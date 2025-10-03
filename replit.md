# Overview

This project is a production-ready Telegram Quiz Bot application deployable anywhere (Render, VPS, Replit, Railway, Heroku). It provides interactive quiz functionality within Telegram chats and groups, includes a Flask web interface for administration, and supports both webhook and polling modes for maximum deployment flexibility. The bot manages quiz questions, tracks user scores and statistics, and offers comprehensive analytics. The goal is to deliver a robust, scalable, and user-friendly quiz experience with advanced administrative capabilities, detailed performance tracking, and seamless deployment on any platform.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application uses a clean, production-ready modular architecture with organized package structure:

**Directory Structure:**
```
src/
├── core/          # Core business logic
│   ├── config.py       # Configuration and environment variables
│   ├── database.py     # SQLite database operations
│   └── quiz.py         # Quiz management logic
├── bot/           # Telegram bot components
│   ├── handlers.py     # Bot command handlers and schedulers
│   └── dev_commands.py # Developer-specific commands
└── web/           # Flask web application
    └── app.py          # Web server, API endpoints, webhook support
main.py            # Entry point for both polling and webhook modes
```

**Components:**
- **Flask Web Application** (src/web/): Admin interface, health checks, webhook endpoint
- **Telegram Bot Handler** (src/bot/): All Telegram bot interactions, schedulers
- **Developer Commands Module** (src/bot/): Developer-specific commands with access control
- **Database Manager** (src/core/): SQLite database operations
- **Quiz Manager** (src/core/): Core business logic for quiz operations and scoring
- **Configuration** (src/core/): Centralized configuration from environment variables
- **Dual-Mode Support**: Polling (VPS/local) and Webhook (Render/Heroku/Railway) modes

## Data Storage
The system uses a **SQLite database** (`data/quiz_bot.db`) for data persistence, including tables for `questions`, `users`, `developers`, `groups`, `user_daily_activity`, `quiz_history`, `activity_logs`, `performance_metrics`, `quiz_stats`, and `broadcast_logs`.

## Frontend Architecture
- **Health Check Endpoint**: GET / returns {"status":"ok"} for platform monitoring
- **Admin Panel**: GET /admin serves Bootstrap-based web interface for question management
- **Templating**: Flask's Jinja2 for server-side rendering
- **API Endpoints**: RESTful API for quiz data management

## Bot Architecture
- **Command Handlers**: Structured processing of commands with cooldowns.
- **Access Control**: Role-based access for administration and developer commands.
- **Developer Commands**: Enhanced commands for quiz management, statistics, and advanced broadcast functionalities.
- **Auto-Clean Feature**: Automatically deletes command and reply messages in groups for cleaner chats.
- **Statistics Tracking**: Comprehensive user and group activity monitoring with time-based analytics.
- **Broadcast System**: Supports various broadcast types (text, media, buttons) with placeholder replacement, live tracking, and auto-cleanup for inactive chats.
- **Memory Management**: Health checks and automatic restart capabilities for stability.
- **Auto Quiz System**: Automatically sends quizzes in DMs and groups upon specific triggers.

## System Design Choices
- **Clean Package Structure**: Organized src/ directory with core/, bot/, web/ modules for maintainability
- **Production-Ready Deployment**: Supports both webhook (Render/Heroku) and polling (VPS) modes
- **Dual-Mode Architecture**: MODE environment variable switches between polling and webhook seamlessly
- **Thread-Safe Webhook**: Background daemon thread with persistent asyncio event loop for webhook mode
- **SQLite Integration**: For improved performance and data integrity
- **Advanced Broadcasts**: Implementation of a versatile broadcast system supporting diverse content types and dynamic placeholders
- **Automated Scheduling**: Quiz scheduling to active groups with persistent scheduling
- **Robust Error Handling & Logging**: Comprehensive logging and error recovery mechanisms
- **Real-time Tracking System**: Comprehensive activity logging and analytics
- **Performance Optimizations**: Database query optimization with indexing, command caching, and concurrent broadcast processing
- **Network Resilience**: HTTPXRequest configuration with balanced timeouts (10s connect, 20s read/write, 10s pool, 8 connections) for automatic reconnection on network failures
- **Single Instance Enforcement**: PID lockfile mechanism (`data/bot.lock`) prevents multiple bot instances from running simultaneously, eliminating Telegram API conflicts
- **Platform-Agnostic**: Works on Render, VPS, Replit, Railway, Heroku with minimal configuration
- **Health Check Compliance**: Simple GET / endpoint for platform health monitoring

# External Dependencies

The project uses a minimal, optimized set of dependencies:

- **python-telegram-bot**: Telegram Bot API wrapper with job queue support for bot functionality and scheduling.
- **Flask**: Web framework for the administrative panel and health checks.
- **apscheduler**: Task scheduling for automated quiz delivery (included with python-telegram-bot).
- **psutil**: System monitoring and memory tracking for performance metrics.
- **httpx**: Async HTTP client used by python-telegram-bot for network resilience (HTTPXRequest with configurable timeouts).
- **gunicorn**: Production WSGI server for deployment.

**Removed Dependencies** (Optimization as of Oct 2025):
- ~~flask-sqlalchemy~~ - Not used (direct SQLite operations instead)
- ~~psycopg2-binary~~ - Not needed (SQLite database, not PostgreSQL)

## External Services
- **Telegram Bot API**: The primary external service for bot operations.
- **Replit Environment**: Hosting platform with port 5000 configuration.

## Environment Variables

**Required (Minimum Setup):**
- **TELEGRAM_TOKEN**: Telegram bot authentication token (get from @BotFather)
- **SESSION_SECRET**: Flask session security key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

**Deployment Configuration:**
- **RENDER_URL**: For Render/production deployment (e.g., https://your-app.onrender.com/webhook)
  - When set, bot automatically uses webhook mode
  - When not set, bot uses polling mode (default)
- **Alternatively, use manual configuration:**
  - **MODE**: `polling` (default, for VPS/local) or `webhook` (for Render/Heroku/Railway)
  - **WEBHOOK_URL**: Your public domain + /webhook (e.g., https://your-app.onrender.com/webhook)

**Optional:**
- **OWNER_ID**: Telegram user ID of the bot owner (get from @userinfobot) - Enables admin features
- **WIFU_ID**: Telegram user ID of additional authorized user

**Deployment Examples:**
- **Local/VPS (Polling Mode)**: `python main.py`
- **Render (Webhook Mode - Simplified)**: Set `RENDER_URL` environment variable, then `gunicorn main:app`
- **Manual Webhook Mode**: `MODE=webhook WEBHOOK_URL=https://your-app.onrender.com/webhook gunicorn main:app`
- **Replit**: Uses polling mode by default - just run `python main.py`