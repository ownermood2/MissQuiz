# Overview

This project is a Telegram Quiz Bot application providing interactive quiz functionality within Telegram chats and groups. It includes a Flask web interface for administration and a Telegram bot for user interaction, managing quiz questions, tracking user scores and statistics, and offering comprehensive analytics. The goal is to deliver a robust, scalable, and user-friendly quiz experience with advanced administrative capabilities and detailed performance tracking.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application uses a modular monolithic architecture, separating concerns into distinct components:
- **Flask Web Application**: Administrative interface for content management.
- **Telegram Bot Handler**: Manages all Telegram bot interactions.
- **Developer Commands Module**: Handles developer-specific commands with access control.
- **Database Manager**: Manages SQLite database operations.
- **Quiz Manager**: Contains core business logic for quiz operations, scoring, and data management.
- **Configuration**: Centralized configuration for access control and settings.
- **Process Management**: Handles application lifecycle, health monitoring, and automatic restarts.

## Data Storage
The system uses a **SQLite database** (`data/quiz_bot.db`) for data persistence, including tables for `questions`, `users`, `developers`, `groups`, `user_daily_activity`, `quiz_history`, `activity_logs`, `performance_metrics`, `quiz_stats`, and `broadcast_logs`.

## Frontend Architecture
- **Admin Panel**: Bootstrap-based web interface for question management.
- **Templating**: Flask's Jinja2 for server-side rendering.

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
- **Modular Design**: Separation of concerns for maintainability.
- **SQLite Integration**: For improved performance and data integrity.
- **Advanced Broadcasts**: Implementation of a versatile broadcast system supporting diverse content types and dynamic placeholders.
- **Automated Scheduling**: Quiz scheduling to active groups with persistent scheduling.
- **Robust Error Handling & Logging**: Comprehensive logging and error recovery mechanisms.
- **Real-time Tracking System**: Comprehensive activity logging and analytics.
- **Performance Optimizations**: Database query optimization with indexing, command caching, and concurrent broadcast processing.

# External Dependencies

- **Flask**: Web framework for the administrative panel.
- **python-telegram-bot**: Library for interacting with the Telegram Bot API.
- **psutil**: Used for system monitoring.
- **Telegram Bot API**: The primary external service for bot operations.
- **Replit Environment**: Hosting platform, requiring specific port configurations.

## Environment Variables
- **TELEGRAM_TOKEN**: Essential for Telegram bot authentication.
- **SESSION_SECRET**: Used for Flask session security.