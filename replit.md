# Overview

This project is a Telegram Quiz Bot application designed to provide interactive quiz functionality within Telegram chats and groups. It features a Flask web interface for administration and a Telegram bot for user interaction. The bot manages quiz questions, tracks user scores and statistics, and offers comprehensive analytics through both web and bot interfaces. The project aims to deliver a robust, scalable, and user-friendly quiz experience with advanced administrative capabilities and detailed performance tracking.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application employs a modular monolithic architecture, separating concerns into distinct components:
- **Flask Web Application**: Administrative interface for content management.
- **Telegram Bot Handler**: Manages all Telegram bot interactions and user commands.
- **Developer Commands Module**: Handles developer-specific commands with enhanced features and access control.
- **Database Manager**: Manages all SQLite database operations for data persistence.
- **Quiz Manager**: Contains the core business logic for quiz operations, scoring, and data management.
- **Configuration**: Centralized configuration for access control and settings.
- **Process Management**: Handles application lifecycle, health monitoring, and automatic restarts.

## Data Storage
The system utilizes a **SQLite database** (`data/quiz_bot.db`) for robust data management, including tables for `questions`, `users`, `developers`, `groups`, `user_daily_activity`, and `quiz_history`.

## Frontend Architecture
- **Admin Panel**: Bootstrap-based web interface for question management.
- **Templating**: Flask's Jinja2 for server-side rendering.

## Bot Architecture
- **Command Handlers**: Structured processing of commands with cooldowns.
- **Access Control**: Role-based access for administration and developer commands (OWNER/WIFU).
- **Developer Commands**: Enhanced commands for quiz deletion, developer management, statistics, bot restarts, and advanced broadcast functionalities (with media, buttons, and placeholders).
- **Auto-Clean Feature**: Automatically deletes command and reply messages in groups for a cleaner chat experience.
- **Statistics Tracking**: Comprehensive user and group activity monitoring with time-based analytics.
- **Broadcast System**: Supports various broadcast types (text, media, buttons) with smart placeholder replacement, live tracking, and auto-cleanup for inactive chats.
- **Memory Management**: Health checks and automatic restart capabilities to ensure stability.

## System Design Choices
- **Modular Design**: Separation of concerns for maintainability.
- **SQLite Integration**: For improved performance and data integrity over previous JSON file storage.
- **Advanced Broadcasts**: Implementation of a versatile broadcast system supporting diverse content types and dynamic placeholders.
- **Automated Scheduling**: Quiz scheduling to active groups with persistent scheduling across restarts.
- **Robust Error Handling & Logging**: Comprehensive logging and error recovery mechanisms.

# External Dependencies

- **Flask**: Web framework for the administrative panel.
- **python-telegram-bot**: Library for interacting with the Telegram Bot API.
- **psutil**: Used for system monitoring, particularly memory usage.
- **Telegram Bot API**: The primary external service for bot operations.
- **Replit Environment**: Hosting platform, requiring specific port configurations (e.g., 5000).

## Environment Variables
- **TELEGRAM_TOKEN**: Essential for Telegram bot authentication.
- **SESSION_SECRET**: Used for Flask session security.

# Recent Changes

## Version 2.3 - October 1, 2025

### 🎯 Auto Quiz System (NEW)
**Auto-send quizzes automatically in DMs and groups:**
1. **Auto-Quiz on /start in DM**: When user sends /start in DM, bot waits 5 seconds then sends first quiz automatically
2. **Auto-Quiz on Bot Added to Group**: When bot is added to group, waits 5 seconds then sends first quiz
3. **Auto-Delete Old Quiz**: Before sending new quiz, automatically deletes the previous quiz message (tracked per chat)
4. **Quiz Message Tracking**: Stores last_quiz_message_id for each chat in database
5. **Non-blocking Implementation**: Uses asyncio for 5-second delays without blocking event loop

### 📊 Enhanced Live Statistics
**Real-time tracking with beautiful formatted output:**
- **Total Groups**: Count of all groups in database
- **Total Users**: Count of all users in database  
- **Quizzes Today**: Current date aggregation
- **Quizzes This Week**: Last 7 days aggregation
- **Quizzes This Month**: Current month aggregation
- **All-Time Total**: Sum of all quiz records
- **/stats Command**: Shows formatted output with emojis and thousand separators
- **Auto-increment**: Every quiz sent updates statistics automatically

### 📝 Broadcast Logging System
**Complete audit trail for all broadcasts:**
- New broadcast_logs table stores every broadcast
- Captures: admin_id, message_text, recipients, success/fail/skip counts, timestamp
- Automatic logging after each broadcast
- Historical data persists across restarts

### 🗄️ Database Enhancements
**New Tables:**
- `quiz_stats` - Daily quiz count tracking
- `broadcast_logs` - Broadcast history tracking

**New Columns:**
- `users.last_quiz_message_id` - Tracks last quiz in DMs
- `groups.last_quiz_message_id` - Tracks last quiz in groups

**New Methods:**
- Quiz tracking: update_last_quiz_message(), get_last_quiz_message()
- Statistics: increment_quiz_count(), get_quiz_stats_*()
- Logging: log_broadcast(), get_total_quizzes_sent()

### 📢 Advanced Broadcast System
**Complete overhaul with professional features:**

**1. Media Support**
- Photo, video, document, animation support
- Caption preservation with placeholder replacement
- Auto-truncation to 1024 chars (Telegram limit)
- Media previews in confirmation

**2. Inline Buttons**
- JSON format: `/broadcast Hello! [["Button","URL"]]`
- Multiple buttons per row, multiple rows supported
- URL validation (http/https/t.me only)
- Works with ALL media types
- Button limits enforced (8/row, 100 total)

**3. Smart Placeholders**
- {first_name}, {username}, {chat_title}, {bot_name}
- Dynamic values for each recipient
- Performance optimized (uses database data)
- Bot name cached once per broadcast

**4. Auto-Cleanup**
- Removes blocked/kicked users automatically
- Constrained to specific error strings
- Safety logging for all deletions
- Tracks auto-removed count separately

**5. Enhanced Reporting**
```
✅ Broadcast completed!
📱 PM Sent: 15
👥 Groups Sent: 8
━━━━━━━━━━━━━━━
✅ Total Sent: 23
❌ Failed: 2
🗑️ Auto-Removed: 1
```

**6. Live PM & Group Tracking**
- Real-time PM interaction tracking
- Auto-stores users and groups
- Persistent storage across restarts

### ⚡ Performance Improvements
- Eliminated O(n) API calls in placeholder replacement
- Bot name cached once instead of per-recipient
- Uses database data (no external API calls)
- Smart rate limiting (0.03s only for >20 recipients)
- Instant delivery for small broadcasts

### 🛠️ Technical Enhancements
- Helper methods: parse_inline_buttons(), replace_placeholders()
- Database methods: remove_inactive_user(), remove_inactive_group()
- Robust error handling with detailed logging
- All existing functionality preserved (no breaking changes)