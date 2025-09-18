# Overview

This project is a Telegram Quiz Bot application that enables interactive quiz functionality across Telegram chats and groups. The system combines a Flask web interface for administration with a Telegram bot for user interaction. The bot manages quiz questions, tracks user scores and statistics, and provides comprehensive analytics through both web and bot interfaces.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure
The application follows a modular monolithic architecture with clear separation of concerns:

- **Flask Web Application** (`app.py`) - Serves as the administrative interface for managing quiz content
- **Telegram Bot Handler** (`bot_handlers.py`) - Manages all Telegram bot interactions and user commands
- **Quiz Manager** (`quiz_manager.py`) - Core business logic for quiz operations, scoring, and data management
- **Process Management** (`main.py`, `run_forever.py`) - Handles application lifecycle and automatic restarts

## Data Storage
The application uses a file-based JSON storage system for simplicity and portability:

- **Questions Database** (`data/questions.json`) - Stores quiz questions with multiple choice options
- **User Scores** (`data/scores.json`) - Maintains user scoring information
- **User Statistics** (`data/user_stats.json`) - Tracks detailed user analytics and activity patterns
- **Active Chats** (`data/active_chats.json`) - Manages list of active Telegram chats/groups

## Frontend Architecture
- **Bootstrap-based Admin Panel** - Simple web interface for question management
- **Static Assets** - JavaScript for dynamic form handling and API interactions
- **Template Engine** - Flask's Jinja2 templating for server-side rendering

## Bot Architecture
- **Command Handlers** - Structured command processing with cooldown mechanisms
- **Admin Management** - Role-based access control for bot administration
- **Statistics Tracking** - Comprehensive user and group activity monitoring
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