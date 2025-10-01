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
The system utilizes a **SQLite database** (`data/quiz_bot.db`) for robust data management, including tables for `questions`, `users`, `developers`, `groups`, `user_daily_activity`, `quiz_history`, `activity_logs`, `performance_metrics`, `quiz_stats`, and `broadcast_logs`.

## Frontend Architecture
- **Admin Panel**: Bootstrap-based web interface for question management.
- **Templating**: Flask's Jinja2 for server-side rendering.

## Bot Architecture
- **Command Handlers**: Structured processing of commands with cooldowns.
- **Access Control**: Role-based access for administration and developer commands (OWNER/WIFU).
- **Developer Commands**: Enhanced commands for quiz deletion, developer management, statistics, bot restarts, and advanced broadcast functionalities.
- **Auto-Clean Feature**: Automatically deletes command and reply messages in groups for a cleaner chat experience.
- **Statistics Tracking**: Comprehensive user and group activity monitoring with time-based analytics, including real-time user interaction, quiz tracking, and performance metrics.
- **Broadcast System**: Supports various broadcast types (text, media, buttons) with smart placeholder replacement, live tracking, auto-cleanup for inactive chats, and a complete logging system.
- **Memory Management**: Health checks and automatic restart capabilities to ensure stability.
- **Auto Quiz System**: Automatically sends quizzes in DMs and groups upon specific triggers (e.g., `/start` command, bot added to group) with auto-deletion of previous quiz messages.

## System Design Choices
- **Modular Design**: Separation of concerns for maintainability.
- **SQLite Integration**: For improved performance and data integrity.
- **Advanced Broadcasts**: Implementation of a versatile broadcast system supporting diverse content types and dynamic placeholders.
- **Automated Scheduling**: Quiz scheduling to active groups with persistent scheduling across restarts.
- **Robust Error Handling & Logging**: Comprehensive logging and error recovery mechanisms.
- **Real-time Tracking System**: Comprehensive activity logging and analytics for all bot interactions.
- **Performance Optimizations**: Database query optimization with indexing, command caching, and concurrent broadcast processing.

# External Dependencies

- **Flask**: Web framework for the administrative panel.
- **python-telegram-bot**: Library for interacting with the Telegram Bot API.
- **psutil**: Used for system monitoring, particularly memory usage.
- **Telegram Bot API**: The primary external service for bot operations.
- **Replit Environment**: Hosting platform, requiring specific port configurations (e.g., 5000).

## Environment Variables
- **TELEGRAM_TOKEN**: Essential for Telegram bot authentication.
- **SESSION_SECRET**: Used for Flask session security.