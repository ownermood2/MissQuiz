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

## Version 2.4 - October 1, 2025 (LATEST)

### 🎯 Professional Real-Time Tracking System (NEW)
**Complete activity monitoring and analytics platform:**

**1. Activity Logs Database**
- New `activity_logs` table tracks ALL bot activities in real-time
- Activity types: command, quiz_sent, quiz_answer, quiz_deleted, group_join, user_join, error, api_call
- Full context: user_id, chat_id, username, chat_title, command, details (JSON), timestamp
- Response time tracking for performance monitoring
- Comprehensive indexes for efficient queries

**2. Real-Time User Interaction Tracking**
- Every command (24+) logged immediately with full context
- All bot_handlers.py commands: /start, /quiz, /help, /mystats, /leaderboard, /stats, etc.
- All dev_commands.py commands: /broadcast, /delquiz, /dev, /stats, /allreload, /performance
- Response time measurement for each command
- Error tracking with detailed error messages

**3. Comprehensive Quiz Tracking**
- Every quiz sent logged with: question_id, chat_type, auto_sent flag, scheduled flag
- Every quiz answer logged with: correctness, selected_answer, user context
- Quiz deletion events tracked separately (activity_type='quiz_deleted')
- Full lifecycle tracking from send → answer → delete

**4. Real-Time Analytics System**
- 9 new analytics methods using live database queries:
  * get_command_usage_stats() - Command usage tracking
  * get_quiz_performance_stats() - Quiz metrics with success rates
  * get_user_engagement_stats() - Active users today/week/month
  * get_hourly_activity_stats() - Activity breakdown by hour
  * get_error_rate_stats() - Error tracking and common errors
  * get_broadcast_stats() - Broadcast performance metrics
  * get_response_time_stats() - Average response times by command
  * get_user_quiz_stats_realtime() - Live user statistics
  * get_leaderboard_realtime() - Real-time rankings
- Eliminated JSON file dependencies - 100% database-driven analytics

**5. Performance Metrics Tracking**
- New `performance_metrics` table for system monitoring
- Memory usage tracking (every 5 minutes)
- Response time logging for all commands
- API call tracking (Telegram API)
- Error rate monitoring
- Uptime tracking with bot start time
- 7-day data retention with automated cleanup

**6. Enhanced Live Dashboard**
- **/stats Command**: Comprehensive real-time dashboard showing:
  * User & Group metrics (total users, total groups, active today/week)
  * Quiz activity (today/week/month with counts)
  * Performance metrics (avg response time, commands executed, error rate)
  * Top 5 commands (last 7 days)
  * Live activity feed (last 10 activities with relative timestamps)
- **/performance Command**: System performance metrics:
  * Average response time
  * Total API calls
  * Error rate percentage
  * System uptime
  * Memory usage (current and average)
- Real-time updates - all data from live database queries
- Relative time formatting ("5m ago", "2h ago", "3d ago")

**7. Data Retention & Maintenance**
- Activity logs: 30-day retention (cleanup at 3 AM daily)
- Performance metrics: 7-day retention (cleanup at 2 AM daily)
- Automated database maintenance with scheduled jobs
- Efficient queries with comprehensive indexing

### 🛠️ Database Schema Updates
**New Tables:**
- `activity_logs` - Comprehensive activity tracking (11 columns)
- `performance_metrics` - System performance monitoring (7 columns)

**New Indexes (9 total):**
- idx_activity_logs_timestamp
- idx_activity_logs_type
- idx_activity_logs_user
- idx_activity_logs_chat
- idx_activity_logs_type_time
- idx_activity_logs_command
- idx_activity_logs_user_time
- idx_performance_metrics_timestamp
- idx_performance_metrics_type_time

**New Scheduled Jobs:**
- track_memory_usage (every 5 minutes)
- cleanup_performance_metrics (daily at 2 AM)
- cleanup_old_activities (daily at 3 AM)

### ✅ Production-Ready Features
- All logging happens in real-time (immediate on action)
- Efficient database queries with proper indexes
- Comprehensive error handling with fallbacks
- Memory-efficient with automated cleanup
- Fail-silent performance tracking (doesn't affect bot performance)
- 100% database-driven (no JSON dependencies)
- Production-tested and architect-approved

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