# Overview

This project is a Telegram Quiz Bot application that enables interactive quiz functionality across Telegram chats and groups. The system combines a Flask web interface for administration with a Telegram bot for user interaction. The bot manages quiz questions, tracks user scores and statistics, and provides comprehensive analytics through both web and bot interfaces.

**Version 2.0** includes major upgrades:
- SQLite database for better performance and data integrity
- Enhanced developer commands with access control
- Auto-clean feature for group-friendly behavior
- Broadcast capabilities
- Comprehensive statistics (today, week, month, all-time)

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application follows a modular monolithic architecture with clear separation of concerns:

- **Flask Web Application** (`app.py`) - Serves as the administrative interface for managing quiz content
- **Telegram Bot Handler** (`bot_handlers.py`) - Manages all Telegram bot interactions and user commands
- **Developer Commands Module** (`dev_commands.py`) - Handles all developer-only commands with enhanced features (NEW)
- **Database Manager** (`database_manager.py`) - SQLite database operations for all data persistence (NEW)
- **Quiz Manager** (`quiz_manager.py`) - Core business logic for quiz operations, scoring, and data management
- **Configuration** (`config.py`) - Centralized configuration for OWNER/WIFU access control (NEW)
- **Process Management** (`main.py`, `run_forever.py`) - Handles application lifecycle and automatic restarts
- **Migration Script** (`migrate_to_sqlite.py`) - One-time migration from JSON to SQLite (NEW)

## Data Storage
The application now uses **SQLite database** for robust and efficient data management:

- **SQLite Database** (`data/quiz_bot.db`) - Primary data store with the following tables:
  - `questions` - Quiz questions with options and correct answers
  - `users` - User information and statistics
  - `developers` - Developer access management
  - `groups` - Active chat/group information
  - `user_daily_activity` - Daily activity tracking per user
  - `quiz_history` - Complete history of all quiz attempts

**Legacy JSON Files** (kept for backup):
- `data/questions.json` - Original questions database
- `data/user_stats.json` - Original user statistics
- `data/developers.json` - Original developer list
- `data/active_chats.json` - Original active chats

## Frontend Architecture
- **Bootstrap-based Admin Panel** - Simple web interface for question management
- **Static Assets** - JavaScript for dynamic form handling and API interactions
- **Template Engine** - Flask's Jinja2 templating for server-side rendering

## Bot Architecture
- **Command Handlers** - Structured command processing with cooldown mechanisms
- **Admin Management** - Role-based access control for bot administration
- **Developer Commands** - Enhanced developer-only commands with strict access control (NEW):
  - `/delquiz` - Delete quiz questions (FIXED - no more Markdown errors)
  - `/dev` - Manage developers (add, remove, list)
  - `/stats` - Enhanced statistics (today, week, month, all-time)
  - `/allreload` - Global bot restart
  - `/broadband` - Simple broadcast without forward tags
  - `/broadcast` - Enhanced broadcast with reply-to and direct message support
- **Auto-Clean Feature** - Automatically deletes command/reply messages after 5 seconds for clean groups (NEW)
- **Access Control** - Only OWNER and WIFU can use developer commands (NEW)
- **Statistics Tracking** - Comprehensive user and group activity monitoring with time-based analytics
- **Memory Management** - Built-in health checks and automatic restart capabilities

## Process Management
- **Health Monitoring** - Memory usage tracking and automatic restarts
- **Keep-Alive Service** - Flask server for uptime monitoring
- **Error Recovery** - Automatic restart mechanisms with exponential backoff
- **Logging System** - Comprehensive logging to both console and files

# External Dependencies

## Core Framework Dependencies
- **Flask** - Web application framework for the admin interface
- **python-telegram-bot** - Telegram Bot API wrapper for bot functionality
- **psutil** - System monitoring for health checks and memory management

## Infrastructure Services
- **Telegram Bot API** - Primary interface for user interactions
- **UptimeRobot** (implied) - External monitoring service for bot availability
- **Replit Environment** - Hosting platform with specific port requirements (5000)

## Optional Integrations
The architecture supports future integration with database systems (Drizzle ORM compatibility mentioned), suggesting potential migration from file-based storage to relational databases.

## Environment Variables
- **TELEGRAM_TOKEN** - Required for Telegram bot authentication
- **SESSION_SECRET** - Flask session security (with fallback default)

# Recent Changes

## Version 2.0 - September 30, 2025

### Major Upgrades
1. **SQLite Database Integration**
   - Migrated from JSON files to SQLite database
   - Better performance and data integrity
   - Comprehensive schema with proper indexes
   - Migration script provided for data transfer

2. **Enhanced Developer Commands**
   - Fixed `/delquiz` Markdown parsing errors
   - Enhanced `/dev` command for developer management
   - Upgraded `/stats` with today/week/month/all-time statistics
   - Added `/allreload` for bot restarts
   - Added `/broadband` for simple broadcasts
   - Enhanced `/broadcast` with reply-to support
   - Added `/delbroadcast` for deleting broadcast messages

3. **Access Control System**
   - Strict OWNER and WIFU access control
   - Friendly unauthorized message for other users
   - Configurable via `config.py`
   - Cannot remove OWNER/WIFU from developers

4. **Auto-Clean Feature**
   - Commands auto-delete after 5 seconds
   - Keeps group chats clean and organized
   - Configurable delay per command
   - Group-friendly behavior

5. **Comprehensive Logging**
   - All developer actions logged
   - Detailed error tracking
   - Success/failure reporting
   - User action attribution

6. **Broadcast System**
   - Plain text broadcasts (`/broadband`)
   - Message forwarding (`/broadcast` with reply)
   - Direct message sending (`/broadcast` with text)
   - Delete broadcasts (`/delbroadcast`)
   - Confirmation before sending
   - Rate limiting to prevent Telegram blocks
   - Success/failure statistics

7. **Automatic Quiz Scheduling**
   - Sends quiz every 30 minutes to all active groups
   - Persistent scheduling across bot restarts
   - Admin reminders when questions run low

### Bug Fixes
- Fixed `/delquiz` Markdown parsing error (Can't parse entities)
- Fixed stats button callback handler
- Improved error handling across all commands
- Fixed bot token exposure in logs (httpx logger set to WARNING level)
- Fixed `/dev list` to show both developer name and user ID
- Fixed `/allreload` slow restart issue (corrected os.execv call)
- Enhanced `/delquiz` to remember quiz ID (no ID needed for /delquiz_confirm)
- Updated `/stats` with emoji-rich format and smart number formatting (K/M)

### Documentation
- Created `DEVELOPER_COMMANDS.md` with complete command guide
- Updated `replit.md` with new architecture
- Added `config.py` for centralized configuration
- Comprehensive inline code documentation

### Files Added
- `config.py` - Configuration for OWNER/WIFU access
- `database_manager.py` - SQLite database management
- `dev_commands.py` - Enhanced developer commands module
- `migrate_to_sqlite.py` - JSON to SQLite migration script
- `DEVELOPER_COMMANDS.md` - Complete developer commands guide
- `data/quiz_bot.db` - SQLite database file

### Technical Improvements
- Modular architecture with separation of concerns
- Type hints for better code maintainability
- Context managers for database connections
- Async/await for non-blocking operations
- Rate limiting for broadcast operations
- Proper exception handling throughout
- Security hardening: Bot token protected in logs
- Production-ready logging configuration