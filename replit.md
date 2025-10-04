# Overview

This project is a production-ready Telegram Quiz Bot application designed for interactive quiz functionality in Telegram chats and groups. It includes a Flask web interface for administration, supports both webhook and polling deployment modes, and manages quiz questions, tracks user scores, and provides analytics. The primary goal is to deliver a robust, scalable, and user-friendly quiz experience with advanced administrative capabilities and seamless deployment across various platforms.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application employs a modular, production-ready architecture with a clear package structure:
```
src/
├── core/          # Core business logic (config, database, quiz)
├── bot/           # Telegram bot components (handlers, dev_commands)
└── web/           # Flask web application (app.py)
main.py            # Entry point
```

**Key Components:**
- **Flask Web Application**: Provides an admin interface, health checks, and a webhook endpoint. Uses an `_AppProxy` pattern for deferred initialization.
- **Telegram Bot Handler**: Manages all Telegram bot interactions, commands, and schedulers, including developer-specific commands with access control.
- **Database Manager**: Handles database operations with dual-backend support (PostgreSQL for production, SQLite for development).
- **Quiz Manager**: Contains the core business logic for quiz operations and scoring.
- **Configuration**: Centralized management of environment variables with lazy validation.
- **Dual-Mode Support**: Automatically detects and operates in either polling (for VPS/local) or webhook (for Render/Heroku/Railway) modes.

## Data Storage
The system supports dual database backends with automatic detection:
-   **PostgreSQL (Production - Recommended)**: Used when `DATABASE_URL` is set, offering persistent storage and scalability. Supports `BIGINT` for Telegram IDs.
-   **SQLite (Development/Local)**: Used by default, file-based (`data/quiz_bot.db`), suitable for local development.

The database schema includes tables for `questions`, `users`, `developers`, `groups`, `user_daily_activity`, `quiz_history`, `activity_logs`, `performance_metrics`, `quiz_stats`, and `broadcast_logs`.

## Frontend Architecture
-   **Health Check Endpoint**: `/` returns `{"status":"ok"}`.
-   **Admin Panel**: `/admin` provides a Bootstrap-based web interface for question management.
-   **Templating**: Flask's Jinja2 for server-side rendering.
-   **API Endpoints**: RESTful API for quiz data management.

## Bot Architecture
-   **Command Handlers**: Structured command processing with cooldowns.
-   **Access Control**: Role-based access for admin and developer commands.
-   **Auto-Clean Feature**: Deletes command and reply messages in groups for cleaner chats.
-   **Statistics Tracking**: Comprehensive user and group activity monitoring.
-   **Broadcast System**: Supports various broadcast types (text, media, buttons) with placeholders, live tracking, and auto-cleanup.
-   **Auto Quiz System**: Sends quizzes in DMs and groups based on triggers.

## System Design Choices
-   **Production-Ready Deployment**: Supports both webhook and polling modes.
-   **No Import-Time Side Effects**: Lazy initialization prevents gunicorn crashes.
-   **Dual-Mode Architecture**: Auto-detects mode based on environment variables.
-   **Docker Support**: Multi-stage Dockerfile and docker-compose for local testing.
-   **Advanced Broadcasts**: Versatile broadcast system.
-   **Automated Scheduling**: Persistent quiz scheduling to active groups.
-   **Robust Error Handling & Logging**: Comprehensive logging and error recovery.
-   **Real-time Tracking System**: Activity logging and analytics.
-   **Performance Optimizations**: Database query optimization, command caching, concurrent broadcast processing, user info caching, and batch activity logging.
-   **Network Resilience**: Configured HTTPXRequest with balanced timeouts.
-   **Single Instance Enforcement**: PID lockfile prevents multiple bot instances.
-   **Platform-Agnostic**: Compatible with Render, VPS, Replit, Railway, Heroku.
-   **Health Check Compliance**: Simple GET `/` endpoint.

# External Dependencies

-   **python-telegram-bot**: Telegram Bot API wrapper, including job queue support.
-   **Flask**: Web framework for the administrative panel and health checks.
-   **apscheduler**: Task scheduling (integrated with `python-telegram-bot`).
-   **psutil**: System monitoring and memory tracking.
-   **httpx**: Async HTTP client used by `python-telegram-bot`.
-   **gunicorn**: Production WSGI server.

## External Services
-   **Telegram Bot API**: Primary external service for bot operations.
-   **Replit Environment**: Hosting platform.

## Environment Variables
-   **Required**: `TELEGRAM_TOKEN`, `SESSION_SECRET`.
-   **Database**: `DATABASE_URL` (for PostgreSQL).
-   **Deployment**: `RENDER_URL` (for Render/webhook auto-detection), or manual `MODE` (`polling`/`webhook`) and `WEBHOOK_URL`.
-   **Optional**: `OWNER_ID`, `WIFU_ID`.