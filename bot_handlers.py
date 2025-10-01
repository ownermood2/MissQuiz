import os
import sys
import logging
import traceback
import asyncio
import json
import psutil
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import List
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    PollAnswerHandler,
    ChatMemberHandler,
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
import config
from database_manager import DatabaseManager
from dev_commands import DeveloperCommands

logger = logging.getLogger(__name__)

class TelegramQuizBot:
    def __init__(self, quiz_manager):
        """Initialize the quiz bot with enhanced features - OPTIMIZED with caching"""
        self.quiz_manager = quiz_manager
        self.application = None
        self.command_cooldowns = defaultdict(lambda: defaultdict(int))
        self.COOLDOWN_PERIOD = 3  # seconds between commands
        self.command_history = defaultdict(lambda: deque(maxlen=10))  # Store last 10 commands per chat
        self.cleanup_interval = 3600  # 1 hour in seconds
        self.bot_start_time = datetime.now()
        
        # OPTIMIZATION: Add stats caching to reduce database queries
        self._stats_cache = None
        self._stats_cache_time = None
        self._stats_cache_duration = timedelta(seconds=30)  # Cache stats for 30 seconds
        
        self.db = DatabaseManager()
        self.dev_commands = DeveloperCommands(self.db, quiz_manager)
        logger.info("TelegramQuizBot initialized with database and developer commands")

    async def ensure_group_registered(self, chat, context: ContextTypes.DEFAULT_TYPE = None):
        """Register group in database for broadcasts - works regardless of admin status"""
        try:
            if chat.type in ["group", "supergroup"]:
                chat_title = chat.title or chat.username or "(No Title)"
                self.db.add_or_update_group(chat.id, chat_title, chat.type)
                logger.debug(f"Registered group {chat.id} ({chat_title}) in database")
        except Exception as e:
            logger.error(f"Failed to register group {chat.id}: {e}")

    async def backfill_groups_startup(self):
        """Migrate active_chats to database groups table on startup"""
        try:
            active_chats = self.quiz_manager.get_active_chats()
            logger.info(f"Backfilling {len(active_chats)} groups from active_chats to database")
            
            registered_count = 0
            for chat_id in active_chats:
                try:
                    chat = await self.application.bot.get_chat(chat_id)
                    if chat.type in ["group", "supergroup"]:
                        chat_title = chat.title or chat.username or "(No Title)"
                        self.db.add_or_update_group(chat.id, chat_title, chat.type)
                        registered_count += 1
                        logger.debug(f"Backfilled group {chat.id} ({chat_title})")
                except Exception as e:
                    logger.warning(f"Failed to backfill group {chat_id}: {e}")
            
            logger.info(f"Successfully backfilled {registered_count}/{len(active_chats)} groups to database")
        except Exception as e:
            logger.error(f"Error in backfill_groups_startup: {e}")

    async def check_admin_status(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot is admin in the chat"""
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            return bot_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def send_admin_reminder(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a professional reminder to make bot admin"""
        try:
            # First check if this is a group chat
            chat = await context.bot.get_chat(chat_id)
            if chat.type not in ["group", "supergroup"]:
                return  # Don't send reminder in private chats

            # Then check if bot is already admin
            is_admin = await self.check_admin_status(chat_id, context)
            if is_admin:
                return  # Don't send reminder if bot is already admin

            reminder_message = """🔔 𝗔𝗱𝗺𝗶𝗻 𝗔𝗰𝗰𝗲𝘀𝘀 𝗡𝗲𝗲𝗱𝗲𝗱

✨ 𝗧𝗼 𝗨𝗻𝗹𝗼𝗰𝗸 𝗔𝗹𝗹 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀:
1️⃣ Open Group Settings
2️⃣ Select Administrators
3️⃣ Add "QuizImpact Bot" as Admin

🎯 𝗬𝗼𝘂'𝗹𝗹 𝗚𝗲𝘁:
• Automatic Quiz Sessions 🤖
• Real-time Leaderboards 📊
• Enhanced Group Features 🌟
• Smooth Quiz Experience ⚡

🎉 Let's make this group amazing together!"""

            keyboard = [[InlineKeyboardButton(
                "✨ Make Admin Now ✨",
                url=f"https://t.me/{chat.username}/administrators"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=chat_id,
                text=reminder_message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent enhanced admin reminder to group {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send admin reminder: {e}")

    async def send_quiz(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, auto_sent: bool = False, scheduled: bool = False, category: str = None) -> None:
        """Send a quiz to a specific chat using native Telegram quiz format"""
        try:
            # Delete last quiz message if it exists (using database tracking)
            last_quiz_msg_id = self.db.get_last_quiz_message(chat_id)
            if last_quiz_msg_id:
                try:
                    await context.bot.delete_message(chat_id, last_quiz_msg_id)
                    logger.info(f"Deleted old quiz message {last_quiz_msg_id} in chat {chat_id}")
                    
                    # Log auto-delete activity
                    self.db.log_activity(
                        activity_type='quiz_deleted',
                        chat_id=chat_id,
                        details={
                            'auto_delete': True,
                            'old_message_id': last_quiz_msg_id
                        },
                        success=True
                    )
                except Exception as e:
                    logger.debug(f"Could not delete old quiz message: {e}")

            # Get a random question for this specific chat (with optional category filter)
            if category:
                logger.info(f"Requesting quiz from category '{category}' for chat {chat_id}")
            question = self.quiz_manager.get_random_question(chat_id, category=category)
            if not question:
                if category:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=f"❌ No questions available in the '{category}' category.\n\n"
                             f"Please try another category or contact the administrator."
                    )
                    logger.warning(f"No questions available for category '{category}' in chat {chat_id}")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="No questions available.")
                    logger.warning(f"No questions available for chat {chat_id}")
                return

            # Ensure question text is clean
            question_text = question['question'].strip()
            if question_text.startswith('/addquiz'):
                question_text = question_text[len('/addquiz'):].strip()
                logger.info(f"Cleaned /addquiz prefix from question for chat {chat_id}")

            logger.info(f"Sending quiz to chat {chat_id}. Question: {question_text[:50]}...")

            # Send the poll
            message = await context.bot.send_poll(
                chat_id=chat_id,
                question=question_text,
                options=question['options'],
                type=Poll.QUIZ,
                correct_option_id=question['correct_answer'],
                is_anonymous=False
            )

            if message and message.poll:
                # Get question ID if available
                question_id = question.get('id')
                
                poll_data = {
                    'chat_id': chat_id,
                    'correct_option_id': question['correct_answer'],
                    'user_answers': {},
                    'poll_id': message.poll.id,
                    'question': question_text,
                    'question_id': question_id,
                    'timestamp': datetime.now().isoformat()
                }
                # Store using proper poll ID key
                context.bot_data[f"poll_{message.poll.id}"] = poll_data
                logger.info(f"Stored quiz data: poll_id={message.poll.id}, chat_id={chat_id}")
                
                # Store new quiz message ID and increment quiz count
                self.db.update_last_quiz_message(chat_id, message.message_id)
                self.db.increment_quiz_count()
                
                self.command_history[chat_id].append(f"/quiz_{message.message_id}")
                
                # Get chat info for logging
                try:
                    chat = await context.bot.get_chat(chat_id)
                    chat_type = 'private' if chat.type == 'private' else 'group'
                    chat_title = chat.title if chat.type in ['group', 'supergroup'] else None
                except Exception:
                    chat_type = 'private' if chat_id > 0 else 'group'
                    chat_title = None
                
                # Log comprehensive quiz_sent activity
                self.db.log_activity(
                    activity_type='quiz_sent',
                    user_id=None,  # No specific user for quiz sending
                    chat_id=chat_id,
                    chat_title=chat_title,
                    details={
                        'question_id': question_id,
                        'question_text': question_text[:100],
                        'chat_type': chat_type,
                        'auto_sent': auto_sent,
                        'scheduled': scheduled,
                        'category': category,
                        'poll_id': message.poll.id,
                        'message_id': message.message_id
                    },
                    success=True
                )
                if category:
                    logger.info(f"Sent quiz from category '{category}' to chat {chat_id}")
                logger.info(f"Logged quiz_sent activity for chat {chat_id} (auto_sent={auto_sent}, scheduled={scheduled})")

        except Exception as e:
            logger.error(f"Error sending quiz: {str(e)}\n{traceback.format_exc()}")
            await context.bot.send_message(chat_id=chat_id, text="Error sending quiz.")

    async def scheduled_cleanup(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Automatically clean old messages every hour"""
        try:
            active_chats = self.quiz_manager.get_active_chats()
            for chat_id in active_chats:
                try:
                    await self.cleanup_old_messages(chat_id, context)
                except Exception as e:
                    logger.error(f"Error cleaning messages in chat {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error in scheduled cleanup: {e}")
    
    async def track_memory_usage(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Track memory usage every 5 minutes for performance monitoring"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.db.log_performance_metric(
                metric_type='memory_usage',
                value=memory_mb,
                unit='MB',
                details={'pid': process.pid}
            )
            
            logger.debug(f"Memory usage tracked: {memory_mb:.2f} MB")
        except Exception as e:
            logger.debug(f"Error tracking memory usage (non-critical): {e}")
    
    async def cleanup_performance_metrics(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clean up performance metrics older than 7 days"""
        try:
            deleted_count = self.db.cleanup_old_performance_metrics(days=7)
            logger.info(f"Cleaned up {deleted_count} old performance metrics")
        except Exception as e:
            logger.error(f"Error cleaning up performance metrics: {e}")
    
    async def cleanup_old_activities(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clean up old activity logs (keep 30 days)"""
        try:
            deleted = self.db.cleanup_old_activities(days=30)
            logger.info(f"Cleaned up {deleted} old activity logs")
        except Exception as e:
            logger.error(f"Error cleaning up old activities: {e}")
    
    def track_api_call(self, api_name: str):
        """Track Telegram API call for performance monitoring"""
        try:
            self.db.log_performance_metric(
                metric_type='api_call',
                metric_name=api_name,
                value=1,
                unit='count'
            )
        except Exception as e:
            logger.debug(f"Error tracking API call (non-critical): {e}")
    
    def track_error(self, error_type: str):
        """Track error for performance monitoring"""
        try:
            self.db.log_performance_metric(
                metric_type='error',
                metric_name=error_type,
                value=1,
                unit='count'
            )
        except Exception as e:
            logger.debug(f"Error tracking error metric (non-critical): {e}")

    def _register_callback_handlers(self):
        """Register all callback query handlers"""
        # Register callback for clearing quizzes
        self.application.add_handler(CallbackQueryHandler(
            self.handle_clear_quizzes_callback,
            pattern="^clear_quizzes_confirm_(yes|no)$"
        ))
        
        # Register callback for stats dashboard
        self.application.add_handler(CallbackQueryHandler(
            self.handle_stats_callback,
            pattern="^(refresh_stats|stats_)"
        ))
        
        # Register callback for devstats dashboard
        self.application.add_handler(CallbackQueryHandler(
            self.handle_devstats_callback,
            pattern="^devstats_"
        ))
        
        # Register callback for activity stream
        self.application.add_handler(CallbackQueryHandler(
            self.handle_activity_callback,
            pattern="^activity_"
        ))
        
        logger.info("Registered all callback handlers")
            
    async def initialize(self, token: str):
        """Initialize and start the bot"""
        try:
            # Build application
            self.application = (
                Application.builder()
                .token(token)
                .build()
            )

            # Add handlers for all commands
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("quiz", self.quiz_command))
            self.application.add_handler(CommandHandler("category", self.category))
            self.application.add_handler(CommandHandler("mystats", self.mystats))
            self.application.add_handler(CommandHandler("groupstats", self.groupstats))
            self.application.add_handler(CommandHandler("leaderboard", self.leaderboard))

            # Developer commands (legacy - keeping existing)
            self.application.add_handler(CommandHandler("addquiz", self.addquiz))
            self.application.add_handler(CommandHandler("globalstats", self.globalstats))
            self.application.add_handler(CommandHandler("editquiz", self.editquiz))
            self.application.add_handler(CommandHandler("totalquiz", self.totalquiz))
            self.application.add_handler(CommandHandler("clear_quizzes", self.clear_quizzes))
            
            # Enhanced developer commands (from dev_commands module)
            self.application.add_handler(CommandHandler("delquiz", self.dev_commands.delquiz))
            self.application.add_handler(CommandHandler("delquiz_confirm", self.dev_commands.delquiz_confirm))
            self.application.add_handler(CommandHandler("dev", self.dev_commands.dev))
            self.application.add_handler(CommandHandler("stats", self.stats_command))
            self.application.add_handler(CommandHandler("devstats", self.dev_commands.devstats))
            self.application.add_handler(CommandHandler("activity", self.dev_commands.activity))
            self.application.add_handler(CommandHandler("allreload", self.dev_commands.allreload))
            self.application.add_handler(CommandHandler("broadcast", self.dev_commands.broadcast))
            self.application.add_handler(CommandHandler("broadcast_confirm", self.dev_commands.broadcast_confirm))
            self.application.add_handler(CommandHandler("broadband", self.dev_commands.broadband))
            self.application.add_handler(CommandHandler("broadband_confirm", self.dev_commands.broadband_confirm))
            self.application.add_handler(CommandHandler("delbroadcast", self.dev_commands.delbroadcast))
            self.application.add_handler(CommandHandler("delbroadcast_confirm", self.dev_commands.delbroadcast_confirm))
            self.application.add_handler(CommandHandler("performance", self.dev_commands.performance_stats))

            # Handle answers and chat member updates
            self.application.add_handler(PollAnswerHandler(self.handle_answer))
            self.application.add_handler(ChatMemberHandler(self.track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
            
            # Track ALL PM interactions (any message in private chat)
            from telegram.ext import MessageHandler, filters
            self.application.add_handler(
                MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, self.track_pm_interaction)
            )

            # Add callback query handlers for all interactive features
            self.application.add_handler(CallbackQueryHandler(
                self.handle_clear_quizzes_callback,
                pattern="^clear_quizzes_confirm_(yes|no)$"
            ))

            # Add callback query handler for stats dashboard UI
            self.application.add_handler(CallbackQueryHandler(
                self.handle_stats_callback,
                pattern="^(refresh_stats|stats_)"
            ))
            
            # Add callback query handler for start command buttons
            self.application.add_handler(CallbackQueryHandler(
                self.handle_start_callback,
                pattern="^(start_quiz|my_stats|leaderboard|help)$"
            ))
            
            # Add callback query handler for leaderboard pagination
            self.application.add_handler(CallbackQueryHandler(
                self.handle_leaderboard_pagination,
                pattern="^leaderboard_page:"
            ))
            
            # Add callback query handler for leaderboard toggle (group <-> global)
            self.application.add_handler(CallbackQueryHandler(
                self.handle_leaderboard_toggle,
                pattern="^leaderboard_toggle:"
            ))
            
            # Add callback query handler for category selection
            self.application.add_handler(CallbackQueryHandler(
                self.handle_category_callback,
                pattern="^cat_"
            ))

            # Schedule automated quiz job - every 30 minutes
            self.application.job_queue.run_repeating(
                self.send_automated_quiz,
                interval=1800,  # 30 minutes
                first=10  # Start first quiz after 10 seconds
            )

            # Schedule cleanup jobs
            self.application.job_queue.run_repeating(
                self.scheduled_cleanup,
                interval=3600,  # Every hour
                first=300  # Start first cleanup after 5 minutes
            )
            self.application.job_queue.run_repeating(
                self.cleanup_old_polls,
                interval=3600, #Every Hour
                first=300
            )
            # Add question history cleanup job
            self.application.job_queue.run_repeating(
                lambda context: self.quiz_manager.cleanup_old_questions(),
                interval=3600,  # Every hour
                first=600  # Start after 10 minutes
            )
            
            # Add memory usage tracking job
            self.application.job_queue.run_repeating(
                self.track_memory_usage,
                interval=300,  # Every 5 minutes
                first=60  # Start after 1 minute
            )
            
            # Add performance metrics cleanup job
            self.application.job_queue.run_repeating(
                self.cleanup_performance_metrics,
                interval=86400,  # Every 24 hours
                first=3600  # Start after 1 hour
            )
            
            # Add activity logs cleanup job (run at 3 AM daily)
            self.application.job_queue.run_daily(
                self.cleanup_old_activities,
                time=__import__('datetime').time(hour=3, minute=0),
                name='cleanup_old_activities'
            )

            await self.application.initialize()
            await self.application.start()
            
            # Backfill groups from active_chats to database
            # Use bot directly instead of context for startup backfill
            await self.backfill_groups_startup()
            
            await self.application.updater.start_polling()

            return self

        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced tracking when bot is added to or removed from chats"""
        try:
            chat = update.effective_chat
            if not chat:
                return

            result = self.extract_status_change(update.my_chat_member)
            if result is None:
                return

            was_member, is_member = result

            if chat.type in ["group", "supergroup"]:
                if not was_member and is_member:
                    # Bot was added to a group
                    self.quiz_manager.add_active_chat(chat.id)
                    await self.ensure_group_registered(chat, context)
                    await self.send_welcome_message(chat.id, context)

                    # Auto-send quiz after 5 seconds when added to group
                    await asyncio.sleep(5)
                    
                    last_quiz_msg_id = self.db.get_last_quiz_message(chat.id)
                    if last_quiz_msg_id:
                        try:
                            await context.bot.delete_message(chat.id, last_quiz_msg_id)
                            logger.info(f"Deleted old quiz message {last_quiz_msg_id} in group {chat.id}")
                        except Exception as e:
                            logger.debug(f"Could not delete old quiz message: {e}")
                    
                    question = self.quiz_manager.get_random_question(chat.id)
                    if question:
                        question_text = question['question'].strip()
                        if question_text.startswith('/addquiz'):
                            question_text = question_text[len('/addquiz'):].strip()
                        
                        message = await context.bot.send_poll(
                            chat_id=chat.id,
                            question=question_text,
                            options=question['options'],
                            type=Poll.QUIZ,
                            correct_option_id=question['correct_answer'],
                            is_anonymous=False
                        )
                        
                        if message and message.poll:
                            poll_data = {
                                'chat_id': chat.id,
                                'correct_option_id': question['correct_answer'],
                                'user_answers': {},
                                'poll_id': message.poll.id,
                                'question': question_text,
                                'timestamp': datetime.now().isoformat()
                            }
                            context.bot_data[f"poll_{message.poll.id}"] = poll_data
                            
                            self.db.update_last_quiz_message(chat.id, message.message_id)
                            self.db.increment_quiz_count()
                            
                            logger.info(f"Auto-sent quiz to group {chat.id} after bot added")

                    logger.info(f"Bot added to group {chat.title} ({chat.id})")

                elif was_member and not is_member:
                    # Bot was removed from a group
                    self.quiz_manager.remove_active_chat(chat.id)
                    logger.info(f"Bot removed from group {chat.title} ({chat.id})")

        except Exception as e:
            logger.error(f"Error in track_chats: {e}")

    async def _delete_messages_after_delay(self, chat_id: int, message_ids: List[int], delay: int = 5) -> None:
        """Delete messages after specified delay in seconds"""
        try:
            await asyncio.sleep(delay)
            for message_id in message_ids:
                try:
                    await self.application.bot.delete_message(
                        chat_id=chat_id,
                        message_id=message_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete message {message_id} in chat {chat_id}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error in _delete_messages_after_delay: {e}")

    async def send_welcome_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, user=None) -> None:
        """Send unified welcome message when bot joins a group or starts in private chat"""
        try:
            keyboard = [
                [InlineKeyboardButton(
                    "➕ Add to Your Group",
                    url=f"https://t.me/{context.bot.username}?startgroup=true"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Create bot link and personalized greeting with clickable user name
            bot_link = f"[Miss Quiz 𓂀 Bot](https://t.me/{context.bot.username})"
            user_greeting = ""
            if user:
                user_name_link = f"[{user.first_name}](tg://user?id={user.id})"
                user_greeting = f"Hello {user_name_link}! 👋\n\n"

            welcome_message = f"""╔════════════════════════════════╗
║ 🎯 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 {bot_link} 🇮🇳 ║
╚════════════════════════════════╝

{user_greeting}📌 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐘𝐨𝐮'𝐥𝐥 𝐋𝐨𝐯𝐞:
➤ 🕒 Auto Quizzes – Fresh quizzes every 30 mins
➤ 🏆 Leaderboard – Track scores & compete for glory
➤ 📚 Categories – GK, CA, History & more! /category
➤ ⚡ Instant Results – Answers in real-time
➤ 🤫 PM Mode – Clean, clutter-free experience
➤ 🧹 Group Mode – Auto-deletes quiz messages for cleaner chat

──────────────────────────────
📝 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:
/start — Begin your quiz journey 🚀
/help — View all commands 🛠️
/category — Explore quiz topics 📖
/mystats — Check your performance 📊
/leaderboard — View top scorers 🏆

──────────────────────────────
🔥 Add me to your groups & let the quiz fun begin! 🎯"""

            await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

            # Get chat type and handle accordingly
            chat = await context.bot.get_chat(chat_id)
            if chat.type in ["group", "supergroup"]:
                is_admin = await self.check_admin_status(chat_id, context)
                if is_admin:
                    await self.send_quiz(chat_id, context, auto_sent=True, scheduled=False)
                else:
                    await self.send_admin_reminder(chat_id, context)

            logger.info(f"Sent premium welcome message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle quiz answers"""
        try:
            answer = update.poll_answer
            if not answer or not answer.poll_id or not answer.user:
                logger.warning("Received invalid poll answer")
                return

            logger.info(f"Received answer from user {answer.user.id} for poll {answer.poll_id}")

            # Get quiz data from context using proper key
            poll_data = context.bot_data.get(f"poll_{answer.poll_id}")
            if not poll_data:
                logger.warning(f"No poll data found for poll_id {answer.poll_id}")
                return

            # IDEMPOTENCY PROTECTION: Check if this user already answered this poll
            user_answer_key = f'answered_by_user_{answer.user.id}'
            if poll_data.get(user_answer_key):
                logger.warning(f"Poll {answer.poll_id} already answered by user {answer.user.id}, skipping duplicate")
                return
            
            # Mark as processed to prevent duplicate recording
            poll_data[user_answer_key] = True

            # Check if this is a correct answer
            is_correct = poll_data['correct_option_id'] in answer.option_ids
            chat_id = poll_data['chat_id']
            question_id = poll_data.get('question_id')
            selected_answer = answer.option_ids[0] if answer.option_ids else None
            
            # Get user info for logging
            username = answer.user.username if answer.user.username else None
            
            # Update user information in database with current username
            self.db.add_or_update_user(
                user_id=answer.user.id,
                username=answer.user.username,
                first_name=answer.user.first_name,
                last_name=answer.user.last_name
            )
            
            # Calculate response time if timestamp is available
            response_time_ms = None
            if 'timestamp' in poll_data:
                try:
                    quiz_sent_time = datetime.fromisoformat(poll_data['timestamp'])
                    response_time_ms = int((datetime.now() - quiz_sent_time).total_seconds() * 1000)
                except Exception as e:
                    logger.debug(f"Could not calculate response time: {e}")
            
            # Log comprehensive quiz answer activity
            self.db.log_activity(
                activity_type='quiz_answer',
                user_id=answer.user.id,
                chat_id=chat_id,
                username=username,
                details={
                    'poll_id': answer.poll_id,
                    'question_id': question_id,
                    'correct': is_correct,
                    'selected_answer': selected_answer,
                    'correct_answer': poll_data['correct_option_id'],
                    'question_text': poll_data.get('question', '')[:100]
                },
                success=True,
                response_time_ms=response_time_ms
            )

            # Record the answer in poll_data
            poll_data['user_answers'][answer.user.id] = {
                'option_ids': answer.option_ids,
                'is_correct': is_correct,
                'timestamp': datetime.now().isoformat()
            }

            # Record both global and group-specific score
            if is_correct:
                self.quiz_manager.increment_score(answer.user.id)
                logger.info(f"Recorded correct answer for user {answer.user.id}")

            # Record group attempt
            self.quiz_manager.record_group_attempt(
                user_id=answer.user.id,
                chat_id=chat_id,
                is_correct=is_correct
            )
            logger.info(f"Recorded group attempt for user {answer.user.id} in chat {chat_id} (correct: {is_correct})")
            
            # Invalidate stats cache for real-time updates
            self._stats_cache = None
            logger.debug(f"Stats cache invalidated after quiz answer from user {answer.user.id}")

        except Exception as e:
            logger.error(f"Error handling answer: {str(e)}\n{traceback.format_exc()}")

    async def send_friendly_error_message(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a user-friendly error message"""
        error_message = """😅 Oops! Something went a bit wrong.

Don't worry though! You can:
1️⃣ Try the command again
2️⃣ Use /help to see all commands
3️⃣ Start a new quiz with /quiz

We're here to help! 🌟"""
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error sending friendly error message: {e}")

    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /quiz command with loading indicator"""
        start_time = time.time()
        try:
            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/quiz',
                success=True
            )
            
            await self.ensure_group_registered(update.effective_chat, context)
            
            if not await self.check_cooldown(update.effective_user.id, "quiz"):
                await update.message.reply_text("⏳ Please wait a moment before starting another quiz!")
                return

            loading_message = await update.message.reply_text("🎯 Preparing your quiz...")
            
            try:
                await self.send_quiz(update.effective_chat.id, context)
                await loading_message.delete()
                response_time = int((time.time() - start_time) * 1000)
                logger.info(f"/quiz completed in {response_time}ms")
                
                self.db.log_performance_metric(
                    metric_type='response_time',
                    metric_name='/quiz',
                    value=response_time,
                    unit='ms'
                )
            except Exception as e:
                logger.error(f"Error in quiz command: {e}")
                await loading_message.edit_text("❌ Oops! Something went wrong. Try /quiz again!")
                
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.track_error('/quiz_error')
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/quiz',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in quiz command: {e}")
            await self.send_friendly_error_message(update.effective_chat.id, context)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command - Track PM and Group live"""
        start_time = time.time()
        try:
            chat = update.effective_chat
            user = update.effective_user
            
            # Update user information in database with current username
            self.db.add_or_update_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Log command immediately
            self.db.log_activity(
                activity_type='user_join' if chat.type == 'private' else 'group_join',
                user_id=user.id,
                chat_id=chat.id,
                username=user.username,
                chat_title=getattr(chat, 'title', None),
                command='/start',
                details={'chat_type': chat.type},
                success=True
            )
            
            # Live tracking: Mark PM access immediately when user starts bot in private chat
            if chat.type == 'private':
                self.db.set_user_pm_access(user.id, True)
                logger.info(f"✅ PM TRACKED: User {user.id} ({user.first_name}) granted PM access")
            else:
                # Track group interaction
                logger.info(f"✅ GROUP TRACKED: Group {chat.id} ({chat.title})")
            
            self.quiz_manager.add_active_chat(chat.id)
            await self.ensure_group_registered(chat, context)
            await self.send_welcome_message(chat.id, context, user)
            
            # Auto-send quiz after 5 seconds in DM
            if chat.type == 'private':
                await asyncio.sleep(5)
                
                last_quiz_msg_id = self.db.get_last_quiz_message(chat.id)
                if last_quiz_msg_id:
                    try:
                        await context.bot.delete_message(chat.id, last_quiz_msg_id)
                        logger.info(f"Deleted old quiz message {last_quiz_msg_id} in DM {chat.id}")
                    except Exception as e:
                        logger.debug(f"Could not delete old quiz message: {e}")
                
                question = self.quiz_manager.get_random_question(chat.id)
                if question:
                    question_text = question['question'].strip()
                    if question_text.startswith('/addquiz'):
                        question_text = question_text[len('/addquiz'):].strip()
                    
                    message = await context.bot.send_poll(
                        chat_id=chat.id,
                        question=question_text,
                        options=question['options'],
                        type=Poll.QUIZ,
                        correct_option_id=question['correct_answer'],
                        is_anonymous=False
                    )
                    
                    if message and message.poll:
                        poll_data = {
                            'chat_id': chat.id,
                            'correct_option_id': question['correct_answer'],
                            'user_answers': {},
                            'poll_id': message.poll.id,
                            'question': question_text,
                            'timestamp': datetime.now().isoformat()
                        }
                        context.bot_data[f"poll_{message.poll.id}"] = poll_data
                        
                        self.db.update_last_quiz_message(chat.id, message.message_id)
                        self.db.increment_quiz_count()
                        
                        logger.info(f"Auto-sent quiz to DM {chat.id} after /start")
            
            # Log successful completion with response time
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/start completed in {response_time}ms for user {user.id}")
            
            self.db.log_performance_metric(
                metric_type='response_time',
                metric_name='/start',
                value=response_time,
                unit='ms'
            )
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id if update.effective_user else None,
                chat_id=update.effective_chat.id if update.effective_chat else None,
                command='/start',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Error starting the bot. Please try again.")
    
    async def track_pm_interaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Track ANY PM interaction - Live tracking for broadcasts"""
        try:
            user = update.effective_user
            if user:
                self.db.set_user_pm_access(user.id, True)
                logger.debug(f"✅ PM INTERACTION: User {user.id} ({user.first_name}) tracked for broadcasts")
        except Exception as e:
            logger.error(f"Error tracking PM interaction: {e}")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command"""
        start_time = time.time()
        try:
            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/help',
                success=True
            )
            
            await self.ensure_group_registered(update.effective_chat, context)
            
            # Check if user is developer
            is_dev = await self.is_developer(update.message.from_user.id)
            
            # Get user and bot links
            user = update.effective_user
            user_name_link = f"[{user.first_name}](tg://user?id={user.id})"
            bot_link = f"[Miss Quiz 𓂀 Bot](https://t.me/{context.bot.username})"
            
            help_text = f"""╔══════════════════════════════════╗
║ ✨ Miss Quiz 𓂀 Bot - Command Center ║
╚══════════════════════════════════╝

📑 Welcome {user_name_link}!
Here's your complete command guide:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 𝗤𝘂𝗶𝘇 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀
➤ /start       🚀 Begin your quiz journey
➤ /quiz        🎲 Take a quiz now
➤ /category    📖 Explore quiz topics

📊 𝗦𝘁𝗮𝘁𝘀 & 𝗥𝗮𝗻𝗸𝗶𝗻𝗴𝘀
➤ /mystats       📈 View your performance
➤ /leaderboard   🏆 View global rankings"""

            # Add developer commands only for developers
            if is_dev:
                help_text += """

🔐 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀
➤ /dev            👑 Manage developer roles
➤ /stats          📊 Real-time bot stats
➤ /broadcast      📣 Send announcements
➤ /delbroadcast   🗑️ Delete latest broadcast
➤ /addquiz        ➕ Add quiz questions
➤ /editquiz       ✏️ Edit existing questions
➤ /delquiz        🗑️ Delete a quiz
➤ /totalquiz      🔢 Total quiz count
➤ /allreload      🔄 Restart bot globally"""

            help_text += f"""

💡 𝗧𝗶𝗽𝘀 & 𝗧𝗿𝗶𝗰𝗸𝘀
• 🕒 Auto quizzes every 30 mins in groups
• 🤫 PM mode keeps chat clean & simple
• 🧹 Group mode auto-deletes old quiz messages when sending new ones
• ⚡ Stats track your progress in real-time
• 🏆 Compete with friends on the leaderboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Need help? Use /help anytime!
✨ Conquer the Quiz World with {bot_link}!"""

            # Send help message with markdown for clickable links
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"Help message sent to user {update.effective_user.id} in {response_time}ms")
            
            self.db.log_performance_metric(
                metric_type='response_time',
                metric_name='/help',
                value=response_time,
                unit='ms'
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/help',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("Error showing help. Please try again later.")

    async def category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /category command with interactive buttons"""
        start_time = time.time()
        try:
            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/category',
                success=True
            )
            
            # Define available categories
            categories = [
                ("General Knowledge", "🌍"),
                ("Current Affairs", "📰"),
                ("Static GK", "📚"),
                ("Science & Technology", "🔬"),
                ("History", "📜"),
                ("Geography", "🗺"),
                ("Economics", "💰"),
                ("Political Science", "🏛"),
                ("Constitution", "📖"),
                ("Constitution & Law", "⚖"),
                ("Arts & Literature", "🎭"),
                ("Sports & Games", "🎮")
            ]
            
            # Create keyboard with 2 buttons per row
            keyboard = []
            for i in range(0, len(categories), 2):
                row = []
                # First button in row
                cat_name, emoji = categories[i]
                row.append(InlineKeyboardButton(
                    f"{emoji} {cat_name}",
                    callback_data=f"cat_{cat_name}"
                ))
                
                # Second button in row (if exists)
                if i + 1 < len(categories):
                    cat_name, emoji = categories[i + 1]
                    row.append(InlineKeyboardButton(
                        f"{emoji} {cat_name}",
                        callback_data=f"cat_{cat_name}"
                    ))
                
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            category_text = """📚 𝗤𝗨𝗜𝗭 𝗖𝗔𝗧𝗘𝗚𝗢𝗥𝗜𝗘𝗦
━━━━━━━━━━━━━━━━━━━━━

🎯 𝗖𝗵𝗼𝗼𝘀𝗲 𝗮 𝗖𝗮𝘁𝗲𝗴𝗼𝗿𝘆:
Click any button below to get a quiz from that category!

━━━━━━━━━━━━━━━━━━━━━
💡 Tip: More categories coming soon!"""

            await update.message.reply_text(
                category_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/category completed in {response_time}ms")
            
            self.db.log_performance_metric(
                metric_type='response_time',
                metric_name='/category',
                value=response_time,
                unit='ms'
            )
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/category',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error showing categories: {e}")
            await update.message.reply_text("Error showing categories.")


    async def mystats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show personal statistics with proper handling of no data"""
        start_time = time.time()
        try:
            user = update.effective_user
            if not user:
                logger.error("No user found in update")
                await update.message.reply_text("❌ Could not identify user.")
                return

            # Update user information in database with current username
            self.db.add_or_update_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=user.id,
                chat_id=update.effective_chat.id,
                username=user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/mystats',
                success=True
            )

            # Send loading message
            loading_msg = await update.message.reply_text("📊 Loading your stats...")

            try:
                # Get user stats from database in real-time
                stats = self.db.get_user_quiz_stats_realtime(user.id)
                
                # Handle case where user has no stats
                if not stats or not stats.get('total_quizzes', 0):
                    welcome_text = """👋 Welcome to QuizImpact!

🎯 You haven't taken any quizzes yet.
Let's get started:
• Use /quiz to try your first quiz
• Join a group to compete with others
• Track your progress here

Ready to begin? Try /quiz now! 🚀"""
                    await loading_msg.edit_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
                    return

                # Get user rank
                leaderboard = self.db.get_leaderboard_realtime(limit=1000)
                user_rank = next((i+1 for i, u in enumerate(leaderboard) if u['user_id'] == user.id), 'N/A')
                
                # Get username display as clickable Telegram profile link
                username = f"[{user.first_name}](tg://user?id={user.id})"
                
                # Format stats according to user's specification
                quiz_attempts = stats.get('total_quizzes', 0)
                correct_answers = stats.get('correct_answers', 0)
                wrong_answers = stats.get('wrong_answers', 0)

                stats_message = f"""📊 Bot & User Stats Dashboard
━━━━━━━━━━━━━━━━━━━━━━
👮 Stats for: {username}
🏆 Total Quizzes Attempted: • {quiz_attempts}
💡 Your Rank: • {user_rank}

📊 𝗦𝘁𝗮𝘁𝘀 𝗳𝗼𝗿 {username}
══════════════════
🎯 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲
• Total Quizzes: {quiz_attempts}
• Correct Answers: {correct_answers}
• Wrong Answers: {wrong_answers}"""

                await loading_msg.edit_text(
                    stats_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                response_time = int((time.time() - start_time) * 1000)
                logger.info(f"Showed stats to user {user.id} in {response_time}ms")
                
                self.db.log_performance_metric(
                    metric_type='response_time',
                    metric_name='/mystats',
                    value=response_time,
                    unit='ms'
                )

            except Exception as e:
                logger.error(f"Error displaying stats: {e}")
                await loading_msg.edit_text("❌ Error displaying stats. Please try again.")

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id if update.effective_user else None,
                chat_id=update.effective_chat.id,
                command='/mystats',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in mystats: {str(e)}\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Error retrieving stats. Please try again.")

    async def groupstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show group statistics with proper handling of no data"""
        start_time = time.time()
        try:
            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/groupstats',
                success=True
            )
            
            chat = update.effective_chat
            if not chat or not chat.type.endswith('group'):
                await update.message.reply_text("""👥 𝗚𝗿𝗼𝘂𝗽 𝗦𝘁𝗮𝘁𝘀 𝗢𝗻𝗹𝘆

This command works in groups! To use it:
1️⃣ Add me to your group
2️⃣ Make me an admin
3️⃣ Try /groupstats again

🔥 Add me to a group now!""", parse_mode=ParseMode.MARKDOWN)
                return

            # Send loading message
            loading_msg = await update.message.reply_text("📊 Loading group stats...")

            try:
                # Get group stats
                stats = self.quiz_manager.get_group_leaderboard(chat.id)
                
                # Handle case where group has no stats
                if not stats or not stats.get('leaderboard'):
                    welcome_text = f"""👋 Welcome to {chat.title}'s Quiz Arena!

📝 No quizzes taken yet in this group.
To get started:
• Use /quiz to start your first quiz
• Invite friends to compete
• Track group progress here

Ready for a quiz challenge? Try /quiz now! 🎯"""
                    await loading_msg.edit_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
                    return

                # Calculate real-time metrics
                active_now = len([u for u in stats['leaderboard'] if u.get('last_active') == datetime.now().strftime('%Y-%m-%d')])
                participation_rate = (active_now / len(stats['leaderboard'])) * 100 if stats['leaderboard'] else 0

                stats_message = f"""📊 𝗚𝗿𝗼𝘂𝗽 𝗦𝘁𝗮𝘁𝘀: {chat.title}
══════════════════
⚡ 𝗥𝗲𝗮𝗹-𝘁𝗶𝗺𝗲 𝗠𝗲𝘁𝗿𝗶𝗰𝘀
• Active Now: {active_now} users
• Participation: {participation_rate:.1f}%
• Group Score: {stats.get('total_correct', 0)} points

📈 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆 𝗧𝗿𝗮𝗰𝗸𝗶𝗻𝗴
• Today: {stats.get('active_users', {}).get('today', 0)} users
• This Week: {stats.get('active_users', {}).get('week', 0)} users
• Total Members: {stats.get('active_users', {}).get('total', 0)} users

🎯 𝗚𝗿𝗼𝘂𝗽 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲
• Total Quizzes: {stats.get('total_quizzes', 0)}
• Success Rate: {stats.get('group_accuracy', 0)}%
• Active Streak: {stats.get('group_streak', 0)} days"""

                # Add top performers if any exist
                if stats['leaderboard']:
                    stats_message += "\n\n🏆 𝗧𝗼𝗽 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗲𝗿𝘀"
                    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                    for rank, entry in enumerate(stats['leaderboard'][:5], 1):
                        try:
                            user = await context.bot.get_chat(entry['user_id'])
                            username = user.first_name or user.username or "Anonymous"
                            activity_indicator = "🟢" if entry.get('last_active') == datetime.now().strftime('%Y-%m-%d') else "⚪"
                            
                            stats_message += f"""

{medals[rank-1]} {username} {activity_indicator}
• Score: {entry.get('total_attempts', 0)} ({entry.get('accuracy', 0)}%)
• Streak: {entry.get('current_streak', 0)} days
• Last: {entry.get('last_active', 'Never')}"""
                        except Exception as e:
                            logger.error(f"Error getting user info: {e}")
                            continue

                stats_message += """
══════════════════
🔄 Live updates • 🟢 Active today"""

                await loading_msg.edit_text(
                    stats_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                response_time = int((time.time() - start_time) * 1000)
                logger.info(f"Showed group stats in chat {chat.id} in {response_time}ms")
                
                self.db.log_performance_metric(
                    metric_type='response_time',
                    metric_name='/groupstats',
                    value=response_time,
                    unit='ms'
                )

            except Exception as e:
                logger.error(f"Error displaying group stats: {e}")
                await loading_msg.edit_text("❌ Error displaying group stats. Please try again.")

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id if update.effective_user else None,
                chat_id=update.effective_chat.id,
                command='/groupstats',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in groupstats: {e}\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Error retrieving group stats. Please try again.")

    async def globalstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show comprehensive bot statistics - Developer only"""
        start_time = time.time()
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/globalstats',
                success=True
            )

            loading_msg = await update.message.reply_text("📊 Analyzing statistics...")

            try:
                # Get accurate user and group counts
                active_chats = self.quiz_manager.get_active_chats() if hasattr(self.quiz_manager, 'get_active_chats') else []
                
                # Validate if we have any active chats, filter out invalid ones
                valid_active_chats = []
                if active_chats:
                    for chat_id in active_chats:
                        try:
                            # Check if chat_id is a valid integer
                            if isinstance(chat_id, (int, str)) and str(chat_id).lstrip('-').isdigit():
                                valid_active_chats.append(int(chat_id))
                        except Exception:
                            continue
                
                total_groups = len(valid_active_chats)
                
                # Check if we have any valid stats
                if hasattr(self.quiz_manager, 'stats') and self.quiz_manager.stats:
                    valid_stats = {k: v for k, v in self.quiz_manager.stats.items() 
                                 if isinstance(v, dict) and 'total_quizzes' in v}
                    total_users = len(valid_stats)
                else:
                    valid_stats = {}
                    total_users = 0

                # Calculate quiz metrics
                total_attempts = 0
                correct_answers = 0
                today_quizzes = 0
                week_quizzes = 0

                current_date = datetime.now().strftime('%Y-%m-%d')
                week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')

                # Process valid stats only
                for user_stats in valid_stats.values():
                    total_attempts += user_stats.get('total_quizzes', 0)
                    correct_answers += user_stats.get('correct_answers', 0)
                    
                    # Check daily activity if it exists and is valid
                    daily_activity = user_stats.get('daily_activity', {})
                    if isinstance(daily_activity, dict):
                        if current_date in daily_activity and isinstance(daily_activity[current_date], dict):
                            today_quizzes += daily_activity[current_date].get('attempts', 0)
                        
                        # Calculate weekly attempts from valid daily entries
                        for date, stats in daily_activity.items():
                            if isinstance(date, str) and date >= week_start and isinstance(stats, dict):
                                week_quizzes += stats.get('attempts', 0)

                # Calculate success rate (avoid division by zero)
                success_rate = round((correct_answers / max(total_attempts, 1) * 100), 1)

                # Get active groups count (only count if the group has been active today)
                active_groups_now = 0
                if valid_active_chats and hasattr(self.quiz_manager, 'get_group_last_activity'):
                    for chat_id in valid_active_chats:
                        try:
                            last_activity = self.quiz_manager.get_group_last_activity(chat_id)
                            if last_activity == current_date:
                                active_groups_now += 1
                        except Exception:
                            continue

                # Calculate today's active users (with validation)
                today_active_users = 0
                week_active_users = 0
                if valid_stats:
                    for uid, stats in valid_stats.items():
                        last_activity = stats.get('last_activity_date')
                        if last_activity == current_date:
                            today_active_users += 1
                        if last_activity and last_activity >= week_start:
                            week_active_users += 1

                # System metrics
                process = psutil.Process()
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                uptime = (datetime.now() - process.create_time()).total_seconds() / 3600
                
                # Get total questions count safely
                total_questions = 0
                if hasattr(self.quiz_manager, 'questions'):
                    if isinstance(self.quiz_manager.questions, list):
                        total_questions = len(self.quiz_manager.questions)

                # Create the statistics message
                stats_message = f"""📊 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀
════════════════
👥 𝗨𝘀𝗲𝗿𝘀 & 𝗚𝗿𝗼𝘂𝗽𝘀
• Total Users: {total_users}
• Total Groups: {total_groups}
• Active Today: {today_active_users}
• Active This Week: {week_active_users}

📈 𝗤𝘂𝗶𝘇 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆
• Today's Quizzes: {today_quizzes}
• This Week: {week_quizzes}
• Total Attempts: {total_attempts}
• Correct Answers: {correct_answers}
• Success Rate: {success_rate}%

⚡ 𝗥𝗲𝗮𝗹-𝘁𝗶𝗺𝗲 𝗠𝗲𝘁𝗿𝗶𝗰𝘀
• Active Groups Now: {active_groups_now}
• Total Questions: {total_questions}
• Memory: {memory_usage:.1f}MB
• Uptime: {uptime:.1f}h
════════════════"""

                await loading_msg.edit_text(
                    stats_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Displayed global stats to developer {update.effective_user.id}")

            except Exception as e:
                logger.error(f"Error processing stats: {e}", exc_info=True)
                await loading_msg.edit_text(
                    """📊 𝗦𝘆𝘀𝘁𝗲𝗺 𝗦𝘁𝗮𝘁𝘂𝘀

✅ Bot is operational 
✅ System is running
✅ Ready for users

🔄 No activity recorded yet
Start by adding the bot to groups!""",
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            logger.error(f"Error in globalstats: {e}", exc_info=True)
            await update.message.reply_text("❌ Error retrieving statistics. Please try again.")


    async def allreload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced reload functionality with proper instance management and auto-cleanup"""
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Send initial status message
            status_message = await update.message.reply_text(
                "🔄 𝗥𝗲𝗹𝗼𝗮𝗱 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀\n════════════════\n⏳ Saving current state...",
                parse_mode=ParseMode.MARKDOWN
            )

            try:
                # Save current state
                self.quiz_manager.save_data(force=True)
                logger.info("Current state saved successfully")

                # Update status
                await status_message.edit_text(
                    "🔄 𝗥𝗲𝗹𝗼𝗮𝗱 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀\n════════════════\n✅ Current state saved\n⏳ Scanning active chats...",
                    parse_mode=ParseMode.MARKDOWN
                )

                # Get current active chats
                current_chats = set(self.quiz_manager.get_active_chats())
                discovered_chats = set()

                # Scan existing chats
                async def scan_chat(chat_id):
                    try:
                        chat = await context.bot.get_chat(chat_id)
                        if chat.type in ['group', 'supergroup', 'private']:
                            discovered_chats.add(chat_id)
                            logger.info(f"Discovered chat: {chat.title if chat.title else 'Private'} ({chat_id})")
                    except Exception as e:
                        logger.warning(f"Could not scan chat {chat_id}: {e}")

                # Execute all scans concurrently
                scan_tasks = [scan_chat(chat_id) for chat_id in current_chats]
                await asyncio.gather(*scan_tasks, return_exceptions=True)

                # Update active chats
                new_chats = discovered_chats - current_chats
                removed_chats = current_chats - discovered_chats

                for chat_id in new_chats:
                    self.quiz_manager.add_active_chat(chat_id)

                for chat_id in removed_chats:
                    self.quiz_manager.remove_active_chat(chat_id)

                # Reload data and update stats
                self.quiz_manager.load_data()
                self.quiz_manager.update_all_stats()

                # Get updated stats
                stats = self.quiz_manager.get_global_statistics()
                
                # Send success message
                success_message = f"""✅ 𝗥𝗲𝗹𝗼𝗮𝗱 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲
════════════════
📊 𝗦𝘁𝗮𝘁𝘂𝘀:
• Active Chats: {len(discovered_chats):,}
• Users Tracked: {stats['users']['total']:,}
• Questions: {stats['performance']['questions_available']:,}
• Stats Updated: ✅
════════════════
🔄 Auto-deleting in 5s..."""

                await status_message.edit_text(
                    success_message,
                    parse_mode=ParseMode.MARKDOWN
                )

                # Schedule deletion for both command and status messages in groups
                if update.message.chat.type != "private":
                    asyncio.create_task(self._delete_messages_after_delay(
                        chat_id=update.message.chat_id,
                        message_ids=[update.message.message_id, status_message.message_id],
                        delay=5
                    ))

                # Schedule quiz delivery for active chats
                await self.send_automated_quiz(context)
                logger.info("Reload completed successfully")

            except Exception as e:
                error_message = f"""❌ 𝗥𝗲𝗹𝗼𝗮𝗱 𝗘𝗿𝗿𝗼𝗿
════════════════
Error: {str(e)}
════════════════"""
                await status_message.edit_text(
                    error_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.error(f"Error during reload: {e}\n{traceback.format_exc()}")
                raise

        except Exception as e:
            logger.error(f"Error in allreload: {e}\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Error during reload. Please try again.")

    async def leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show context-aware leaderboard - group stats in groups, global in private chats"""
        start_time = time.time()
        try:
            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/leaderboard',
                success=True
            )
            
            # Detect chat type and show appropriate leaderboard
            chat = update.effective_chat
            if chat.type in ['group', 'supergroup']:
                # Show group leaderboard in groups
                scope = 'group'
                logger.info(f"Showing group leaderboard for chat {chat.id}")
            else:
                # Show global leaderboard in private chats
                scope = 'global'
                logger.info(f"Showing global leaderboard for user {update.effective_user.id}")
            
            # Show page 0 by default with detected scope
            await self._show_leaderboard_page(update, context, page=0, scope=scope)
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"Leaderboard ({scope}) shown successfully in {response_time}ms")
            
            self.db.log_performance_metric(
                metric_type='response_time',
                metric_name='/leaderboard',
                value=response_time,
                unit='ms'
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/leaderboard',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error showing leaderboard: {e}\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Error retrieving leaderboard. Please try again.")
    
    async def _show_leaderboard_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0, edit: bool = False, scope: str = 'global') -> None:
        """Display a specific page of the leaderboard (2 entries per page) - supports group and global scopes"""
        try:
            chat = update.effective_chat
            bot_link = f"[Miss Quiz 𓂀 Bot](https://t.me/{context.bot.username})"
            
            # Fetch leaderboard data based on scope
            if scope == 'group':
                # Get group-specific leaderboard
                stats = self.quiz_manager.get_group_leaderboard(chat.id)
                leaderboard = stats.get('leaderboard', [])
                scope_title = f"👥 Group Leaderboard: {chat.title}"
                scope_emoji = "👥"
            else:
                # Get global leaderboard
                leaderboard = self.db.get_leaderboard_realtime(limit=20)
                scope_title = "🌍 Global Leaderboard"
                scope_emoji = "🌍"
            
            # Header
            leaderboard_text = f"""╔════════════════════════════════╗
║ 🏆 {bot_link} 🇮🇳 ║
╚════════════════════════════════╝

{scope_emoji} {scope_title}
✨ Top Quiz Champions - Live Rankings ✨

──────────────────────────────"""

            # If no participants yet
            if not leaderboard:
                leaderboard_text += f"""\n
🎯 No champions yet!
💡 Be the first to claim the throne!

──────────────────────────────
🔥 Use /quiz to start your journey! 🎯"""
                
                keyboard = [[InlineKeyboardButton("🎯 Start Quiz", callback_data="start_quiz")]]
                
                # Add scope toggle if in group
                if chat.type in ['group', 'supergroup']:
                    toggle_scope = 'global' if scope == 'group' else 'group'
                    toggle_label = "🌍 View Global" if scope == 'group' else "👥 View Group"
                    keyboard.insert(0, [InlineKeyboardButton(toggle_label, callback_data=f"leaderboard_toggle:{toggle_scope}:0")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if edit and update.callback_query:
                    await update.callback_query.edit_message_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(leaderboard_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                return

            # Calculate pagination
            entries_per_page = 2
            total_pages = (len(leaderboard) + entries_per_page - 1) // entries_per_page
            page = max(0, min(page, total_pages - 1))  # Clamp page to valid range
            
            start_idx = page * entries_per_page
            end_idx = min(start_idx + entries_per_page, len(leaderboard))
            page_entries = leaderboard[start_idx:end_idx]

            # Add each user's stats with premium styling
            rank_badges = {
                1: "👑",  # Crown for 1st
                2: "💎",  # Diamond for 2nd
                3: "⭐",  # Star for 3rd
            }
            medals = ["🥇", "🥈", "🥉"]
            
            for entry in page_entries:
                try:
                    # Calculate actual rank (1-based)
                    rank = leaderboard.index(entry) + 1
                    
                    # Get user's first name and create clickable profile link
                    user_id = entry.get('user_id')
                    try:
                        # Try to fetch user info from Telegram for clickable link
                        user_info = await context.bot.get_chat(user_id)
                        username = f"[{user_info.first_name}](tg://user?id={user_id})"
                    except:
                        # Fallback: ALWAYS use clickable profile link with user_id
                        first_name = entry.get('first_name', '')
                        db_username = entry.get('username', '')
                        if first_name:
                            username = f"[{first_name}](tg://user?id={user_id})"
                        elif db_username:
                            username = f"[{db_username}](tg://user?id={user_id})"
                        else:
                            username = f"[User](tg://user?id={user_id})"
                    
                    # Rank display
                    if rank <= 3:
                        rank_display = f"{medals[rank-1]} {rank_badges[rank]}"
                    elif rank <= 9:
                        rank_display = f"{rank}️⃣"
                    else:
                        rank_display = f"🔟" if rank == 10 else f"#{rank}"

                    # Format stats based on scope
                    if scope == 'group':
                        # Group leaderboard format
                        score_display = entry.get('score', 0)
                        accuracy = entry.get('accuracy', 0)
                        leaderboard_text += f"""
{rank_display} 𝗥𝗮𝗻𝗸 #{rank} • {username}
💯 Score: {score_display} pts • 🎯 Accuracy: {accuracy}%
┣ ✅ Correct: {entry.get('correct_answers', 0)}
┣ ❌ Wrong: {entry.get('wrong_answers', 0)}
┗ 🔥 Streak: {entry.get('current_streak', 0)} days
──────────────────────────────"""
                    else:
                        # Global leaderboard format
                        score_display = f"{entry['score']/1000:.1f}K" if entry['score'] >= 1000 else str(entry['score'])
                        leaderboard_text += f"""
{rank_display} 𝗥𝗮𝗻𝗸 #{rank} • {username}
💯 Total Score: {score_display} points
┣ ✅ Quizzes: {entry['total_quizzes']}
┣ 🎯 Correct: {entry['correct_answers']}
┗ ❌ Wrong: {entry['wrong_answers']}
──────────────────────────────"""

                except Exception as e:
                    logger.error(f"Error displaying user {entry.get('user_id')}: {e}")
                    continue

            # Professional footer with page info
            leaderboard_text += f"""

📄 Page {page + 1}/{total_pages} • Showing ranks {start_idx + 1}-{end_idx}
📱 Live Tracking – Rankings update in real-time!
🔥 Use /quiz to climb the ranks! 🎯"""

            # Create navigation buttons
            keyboard = []
            
            # Add scope toggle button if in group
            if chat.type in ['group', 'supergroup']:
                toggle_scope = 'global' if scope == 'group' else 'group'
                toggle_label = "🌍 View Global" if scope == 'group' else "👥 View Group"
                keyboard.append([InlineKeyboardButton(toggle_label, callback_data=f"leaderboard_toggle:{toggle_scope}:0")])
            
            # Navigation buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data=f"leaderboard_page:{scope}:{page-1}"))
            
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("⏭ Next", callback_data=f"leaderboard_page:{scope}:{page+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("🎯 Start Quiz", callback_data="start_quiz")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send or edit message
            if edit and update.callback_query:
                await update.callback_query.edit_message_text(
                    leaderboard_text, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    leaderboard_text, 
                    parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"Error showing leaderboard page: {e}\n{traceback.format_exc()}")
            error_msg = "❌ Error displaying leaderboard. Please try again."
            if edit and update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
    
    async def handle_leaderboard_pagination(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle leaderboard page navigation callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Extract scope and page from callback data (format: "leaderboard_page:scope:N")
            parts = query.data.split(":")
            if len(parts) == 3:
                # New format with scope
                scope = parts[1]
                page = int(parts[2])
            else:
                # Legacy format (backwards compatibility)
                page = int(parts[1])
                scope = 'global'
            
            # Show the requested page with scope
            await self._show_leaderboard_page(update, context, page=page, edit=True, scope=scope)
            
        except Exception as e:
            logger.error(f"Error handling leaderboard pagination: {e}\n{traceback.format_exc()}")
            await query.answer("❌ Error loading page", show_alert=True)
    
    async def handle_leaderboard_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle leaderboard scope toggle (group <-> global)"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Extract scope and page from callback data (format: "leaderboard_toggle:scope:page")
            parts = query.data.split(":")
            scope = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 0
            
            # Show leaderboard with new scope
            await self._show_leaderboard_page(update, context, page=page, edit=True, scope=scope)
            logger.info(f"Toggled leaderboard to {scope} scope for user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error handling leaderboard toggle: {e}\n{traceback.format_exc()}")
            await query.answer("❌ Error switching view", show_alert=True)



    async def addquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add new quiz(zes) - Developer only
        
        Usage:
        /addquiz question | option1 | option2 | option3 | option4 | correct_number
        /addquiz --allow-duplicates question | option1 | option2 | option3 | option4 | correct_number
        """
        start_time = time.time()
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/addquiz',
                success=True
            )

            # Extract message content and check for allow_duplicates flag
            message_text = update.message.text
            allow_duplicates = '--allow-duplicates' in message_text or '-d' in message_text
            
            # Remove the command and flags
            message_text = message_text.replace('/addquiz', '').replace('--allow-duplicates', '').replace('-d', '').strip()
            
            if not message_text:
                await update.message.reply_text(
                    "❌ Please provide questions in the correct format.\n\n"
                    "For single question:\n"
                    "/addquiz question | option1 | option2 | option3 | option4 | correct_number\n\n"
                    "For multiple questions (using the | format):\n"
                    "/addquiz question1 | option1 | option2 | option3 | option4 | correct_number\n"
                    "/addquiz question2 | option1 | option2 | option3 | option4 | correct_number\n\n"
                    "To allow duplicate questions:\n"
                    "/addquiz --allow-duplicates question | options...\n\n"
                    "Add more Quiz /addquiz !"
                )
                return

            questions_data = []

            # Split by newlines to handle multiple questions
            lines = message_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or not '|' in line:
                    continue

                parts = line.split("|")
                if len(parts) != 6:
                    continue

                try:
                    correct_answer = int(parts[5].strip()) - 1
                    if not (0 <= correct_answer < 4):
                        continue

                    questions_data.append({
                        'question': parts[0].strip(),
                        'options': [p.strip() for p in parts[1:5]],
                        'correct_answer': correct_answer
                    })
                except (ValueError, IndexError):
                    continue

            if not questions_data:
                await update.message.reply_text(
                    "❌ Please provide questions in the correct format.\n\n"
                    "For single question:\n"
                    "/addquiz question | option1 | option2 | option3 | option4 | correct_number\n\n"
                    "For multiple questions (using the | format):\n"
                    "/addquiz question1 | option1 | option2 | option3 | option4 | correct_number\n"
                    "/addquiz question2 | option1 | option2 | option3 | option4 | correct_number\n\n"
                    "To allow duplicate questions:\n"
                    "/addquiz --allow-duplicates question | options...\n\n"
                    "Add more Quiz /addquiz !"
                )
                return

            # Add questions and get stats
            stats = self.quiz_manager.add_questions(questions_data, allow_duplicates=allow_duplicates)
            total_questions = len(self.quiz_manager.get_all_questions())
            
            # Get database count for verification
            db_questions = self.db.get_all_questions()
            db_count = len(db_questions)

            # Format response message with comprehensive feedback
            duplicate_warning = ""
            if stats['rejected']['duplicates'] > 0 and not allow_duplicates:
                duplicate_warning = f"\n\n⚠️ 𝗗𝘂𝗽𝗹𝗶𝗰𝗮𝘁𝗲 𝗪𝗮𝗿𝗻𝗶𝗻𝗴:\n{stats['rejected']['duplicates']} questions were rejected as duplicates.\nUse /addquiz --allow-duplicates to override."
            
            db_status = "✅" if stats['db_saved'] == stats['added'] else "⚠️"
            
            response = f"""📝 𝗤𝘂𝗶𝘇 𝗔𝗱𝗱𝗶𝘁𝗶𝗼𝗻 𝗥𝗲𝗽𝗼𝗿𝘁
════════════════
✅ Successfully added: {stats['added']} questions
{db_status} Database saved: {stats['db_saved']}/{stats['added']}

👉 𝗧𝗼𝘁𝗮𝗹 𝗤𝘂𝗶𝘇𝘇𝗲𝘀:
• JSON: {total_questions}
• Database: {db_count}

❌ 𝗥𝗲𝗷𝗲𝗰𝘁𝗲𝗱:
• Duplicates: {stats['rejected']['duplicates']}
• Invalid Format: {stats['rejected']['invalid_format']}
• Invalid Options: {stats['rejected']['invalid_options']}{duplicate_warning}
════════════════"""

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/addquiz completed in {response_time}ms - added {stats['added']} quizzes (DB: {stats['db_saved']}, duplicates allowed: {allow_duplicates})")

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/addquiz',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in addquiz: {e}")
            await update.message.reply_text("❌ Error adding quiz.")


    async def editquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show and edit quiz questions - Developer only"""
        start_time = time.time()
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/editquiz',
                details={'args': context.args},
                success=True
            )

            logger.info(f"Processing /editquiz command from user {update.message.from_user.id}")

            # Get all questions for validation
            questions = self.quiz_manager.get_all_questions()
            if not questions:
                await update.message.reply_text(
                    """❌ 𝗡𝗼 𝗤𝘂𝗶𝘇𝘇𝗲𝘀 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲
════════════════
Add new quizzes using /addquiz command
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Handle reply to quiz case
            if update.message.reply_to_message and update.message.reply_to_message.poll:
                poll_id = update.message.reply_to_message.poll.id
                poll_data = context.bot_data.get(f"poll_{poll_id}")

                if not poll_data:
                    await self._handle_quiz_not_found(update, context)
                    return

                # Find the quiz in questions list
                found_idx = -1
                for idx, q in enumerate(questions):
                    if q['question'] == poll_data['question']:
                        found_idx = idx
                        break

                if found_idx == -1:
                    await self._handle_quiz_not_found(update, context)
                    return

                # Show the quiz details
                quiz = questions[found_idx]
                quiz_text = f"""📝 𝗤𝘂𝗶𝘇 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 (#{found_idx + 1})
════════════════

❓ Question: {quiz['question']}
📍 Options:"""
                for i, opt in enumerate(quiz['options'], 1):
                    marker = "✅" if i-1 == quiz['correct_answer'] else "⭕"
                    quiz_text += f"\n{marker} {i}. {opt}"

                quiz_text += f"""
════════════════

To edit this quiz:
/editquiz {quiz['id']}
To delete this quiz:
/delquiz {quiz['id']}"""

                await update.message.reply_text(
                    quiz_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Handle direct command case
            # Parse arguments for pagination
            args = context.args
            page = 1
            per_page = 5

            if args and args[0].isdigit():
                page = max(1, int(args[0]))

            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            total_pages = (len(questions) + per_page - 1) // per_page

            # Adjust page if out of bounds
            if page > total_pages:
                page = total_pages
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page

            # Format questions for display
            questions_text = f"""📝 𝗤𝘂𝗶𝘇 𝗘𝗱𝗶𝘁𝗼𝗿 (Page {page}/{total_pages})
════════════════

📌 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:
• View quizzes: /editquiz [page_number]
• Delete quiz: /delquiz [quiz_number]
• Add new quiz: /addquiz

📊 𝗦𝘁𝗮𝘁𝘀:
• Total Quizzes: {len(questions)}
• Showing: #{start_idx + 1} to #{min(end_idx, len(questions))}

🎯 𝗤𝘂𝗶𝘇 𝗟𝗶𝘀𝘁:"""
            for i, q in enumerate(questions[start_idx:end_idx], start=start_idx + 1):
                questions_text += f"""

📌 𝗤𝘂𝗶𝘇 #{i}
❓ Question: {q['question']}
📍 Options:"""
                for j, opt in enumerate(q['options'], 1):
                    marker = "✅" if j-1 == q['correct_answer'] else "⭕"
                    questions_text += f"\n{marker} {j}. {opt}"
                questions_text += "\n════════════════"

            # Add navigation help
            if total_pages > 1:
                questions_text += f"""

📖 𝗡𝗮𝘃𝗶𝗴𝗮𝘁𝗶𝗼𝗻:"""
                if page > 1:
                    questions_text += f"\n⬅️ Previous: /editquiz {page-1}"
                if page < total_pages:
                    questions_text += f"\n➡️ Next: /editquiz {page+1}"

            # Send the formatted message
            await update.message.reply_text(
                questions_text,
                parse_mode=ParseMode.MARKDOWN
            )
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"Sent quiz list page {page}/{total_pages} to user {update.message.from_user.id} in {response_time}ms")

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/editquiz',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            error_msg = f"Error in editquiz command: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            await update.message.reply_text(
                """❌ 𝗘𝗿𝗿𝗼𝗿
════════════════
Failed to display quizzes. Please try again later.
════════════════""",
                parse_mode=ParseMode.MARKDOWN
            )

    async def _handle_dev_command_unauthorized(self, update: Update) -> None:
        """Handle unauthorized access to developer commands"""
        await update.message.reply_text(
            "⚠️ This command is only available to bot developers.",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.warning(f"Unauthorized access attempt to dev command by user {update.message.from_user.id}")

    async def is_developer(self, user_id: int) -> bool:
        """Check if user is a developer (uses database)"""
        try:
            return self.db.is_developer(user_id)
        except Exception as e:
            logger.error(f"Error checking developer status: {e}")
            return False
            
    async def get_developers(self) -> list:
        """Get list of all developers"""
        try:
            # Load developers from the developers.json file
            import json
            dev_file_path = os.path.join(os.path.dirname(__file__), "data", "developers.json")
            if os.path.exists(dev_file_path):
                with open(dev_file_path, 'r') as f:
                    dev_data = json.load(f)
                    return dev_data.get('developers', [])
            else:
                # Fallback to default developer IDs if file doesn't exist
                return [7653153066]
        except Exception as e:
            logger.error(f"Error getting developers: {e}")
            # Fallback to default developer IDs in case of error
            return [7653153066]
            
    async def save_developers(self, dev_list: list) -> bool:
        """Save the list of developers"""
        try:
            # Create data directory if it doesn't exist
            import json
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            os.makedirs(data_dir, exist_ok=True)
            
            # Save developers to the developers.json file
            dev_file_path = os.path.join(data_dir, "developers.json")
            
            dev_data = {
                "developers": dev_list,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(dev_file_path, 'w') as f:
                json.dump(dev_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving developers: {e}")
            return False

    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send broadcast message to all chats - Developer only - OPTIMIZED with batching"""
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Get broadcast message
            message_text = update.message.text.replace('/broadcast', '', 1).strip()
            if not message_text:
                await update.message.reply_text("❌ Please provide a message to broadcast.")
                return

            # Format broadcast message
            broadcast_message = f"""📢 𝗔𝗻𝗻𝗼𝘂𝗻𝗰𝗲𝗺𝗲𝗻𝘁
════════════════

{message_text}"""

            # Get all active chats
            active_chats = self.quiz_manager.get_active_chats()
            success_count = 0
            failed_count = 0
            
            # OPTIMIZATION: Send messages in batches concurrently with controlled rate limiting
            batch_size = 5
            delay_between_batches = 0.5
            
            for i in range(0, len(active_chats), batch_size):
                batch = active_chats[i:i + batch_size]
                tasks = []
                
                for chat_id in batch:
                    task = context.bot.send_message(
                        chat_id=chat_id,
                        text=broadcast_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    tasks.append(task)
                
                # Wait for all tasks in batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_count += 1
                        logger.error(f"Failed to send broadcast to {batch[idx]}: {result}")
                    else:
                        success_count += 1
                
                # Rate limiting between batches
                if i + batch_size < len(active_chats):
                    await asyncio.sleep(delay_between_batches)

            # Send results
            results = f"""📢 Broadcast Results:
✅ Successfully sent to: {success_count} chats
❌ Failed to send to: {failed_count} chats"""

            result_msg = await update.message.reply_text(results)

            # Auto-delete command and result in groups
            if update.message.chat.type != "private":
                asyncio.create_task(self._delete_messages_after_delay(
                    chat_id=update.message.chat_id,
                    message_ids=[update.message.message_id, result_msg.message_id],
                    delay=5
                ))

            logger.info(f"Broadcast completed (optimized batching): {success_count} successful, {failed_count} failed")

        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await update.message.reply_text("❌ Error sending broadcast. Please try again.")

    async def check_admin_status(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot is admin in the chat"""
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            return bot_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def send_admin_reminder(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a professional reminder to make bot admin"""
        try:
            # First check if this is a group chat
            chat = await context.bot.get_chat(chat_id)
            if chat.type not in ["group", "supergroup"]:
                return  # Don't send reminder in private chats

            # Then check if bot is already admin
            is_admin = await self.check_admin_status(chat_id, context)
            if is_admin:
                return  # Don't send reminder if bot is already admin

            reminder_message = """🔔 𝗔𝗱𝗺𝗶𝗻 𝗥𝗲𝗾𝘂𝗲𝘀𝘁
════════════════
📌 To enable all quiz features, please:
1. Click Group Settings
2. Select Administrators
3. Add "IIı 𝗤𝘂𝗶𝘇𝗶𝗺𝗽𝗮𝗰𝘁𝗕𝗼𝘁 🇮🇳 ıII" as Admin

🎯 𝗕𝗲𝗻𝗲𝗳𝗶𝘁𝘀
• Automatic Quiz Delivery
• Message Management
• Enhanced Group Analytics
• Leaderboard Updates

✨ Upgrade your quiz experience now!
════════════════"""

            await context.bot.send_message(
                chat_id=chat_id,
                text=reminder_message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent admin reminder to group {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send admin reminder: {e}")

    async def scheduled_quiz(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send scheduled quizzes to all active chats"""
        try:
            active_chats = self.quiz_manager.get_active_chats()
            for chat_id in active_chats:
                try:
                    # Check if bot is admin
                    is_admin = await self.check_admin_status(chat_id, context)

                    if is_admin:
                        # Send new quiz with tracking parameters (message cleanup handled elsewhere)
                        await self.send_quiz(chat_id, context, auto_sent=True, scheduled=True)
                        logger.info(f"Sent scheduled quiz to chat {chat_id}")
                    else:
                        # Send admin reminder
                        await self.send_admin_reminder(chat_id, context)
                        logger.info(f"Sent admin reminder to chat {chat_id}")

                except Exception as e:
                    logger.error(f"Error handling chat {chat_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in scheduled quiz: {e}")

    async def check_cooldown(self, user_id: int, command: str) -> bool:
        """Check if command is on cooldown for user"""
        current_time = datetime.now().timestamp()
        last_used = self.command_cooldowns[user_id][command]
        if current_time - last_used < self.COOLDOWN_PERIOD:
            return False
        self.command_cooldowns[user_id][command] = current_time
        return True

    async def cleanup_old_polls(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Remove old poll data to prevent memory leaks"""
        try:
            current_time = datetime.now()
            keys_to_remove = []

            for key, poll_data in context.bot_data.items():
                if not key.startswith('poll_'):
                    continue

                # Remove polls older than 1 hour
                if 'timestamp' in poll_data:
                    poll_time = datetime.fromisoformat(poll_data['timestamp'])
                    if (current_time - poll_time) > timedelta(hours=1):
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                del context.bot_data[key]

            logger.info(f"Cleaned up {len(keys_to_remove)} old poll entries")

        except Exception as e:
            logger.error(f"Error cleaning up old polls: {e}")

    async def delquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show and delete quiz questions - Developer only"""
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Get all questions for validation
            questions = self.quiz_manager.get_all_questions()
            if not questions:
                await update.message.reply_text(
                    """❌ 𝗡𝗼 𝗤𝘂𝗶𝘇𝘇𝗲𝘀 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲
════════════════
Add new quizzes using /addquiz command
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Handle reply to quiz case
            if update.message.reply_to_message and update.message.reply_to_message.poll:
                poll_id = update.message.reply_to_message.poll.id
                poll_data = context.bot_data.get(f"poll_{poll_id}")

                if not poll_data:
                    await self._handle_quiz_not_found(update, context)
                    return

                # Find the quiz in questions list
                found_idx = -1
                for idx, q in enumerate(questions):
                    if q['question'] == poll_data['question']:
                        found_idx = idx
                        break

                if found_idx == -1:
                    await self._handle_quiz_not_found(update, context)
                    return

                # Show confirmation message
                quiz = questions[found_idx]
                confirm_text = f"""🗑 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻
════════════════

📌 𝗤𝘂𝗶𝘇 #{found_idx + 1}
❓ Question: {quiz['question']}

📍 𝗢𝗽𝘁𝗶𝗼𝗻𝘀:"""
                for i, opt in enumerate(quiz['options'], 1):
                    marker = "✅" if i-1 == quiz['correct_answer'] else "⭕"
                    confirm_text += f"\n{marker} {i}. {opt}"

                confirm_text += f"""

⚠️ 𝗧𝗼 𝗰𝗼𝗻𝗳𝗶𝗿𝗺 𝗱𝗲𝗹𝗲𝘁𝗶𝗼𝗻:
/delquiz_confirm {found_idx + 1}

❌ 𝗧𝗼 𝗰𝗮𝗻𝗰𝗲𝗹:
Use any other command or ignore this message
════════════════"""

                await update.message.reply_text(
                    confirm_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Handle direct command case - check if quiz number is provided
            if not context.args:
                await update.message.reply_text(
                    """❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗨𝘀𝗮𝗴𝗲
════════════════
Either:
1. Reply to a quiz message with /delquiz
2. Use: /delquiz [quiz_number]

ℹ️ Use /editquiz to view available quizzes
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            try:
                quiz_num = int(context.args[0])
                if not (1 <= quiz_num <= len(questions)):
                    await update.message.reply_text(
                        f"""❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗤𝘂𝗶𝘇 𝗡𝘂𝗺𝗯𝗲𝗿
════════════════
Please choose a number between 1 and {len(questions)}

ℹ️ Use /editquiz to view available quizzes
════════════════""",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

                # Show confirmation message
                quiz = questions[quiz_num - 1]
                confirm_text = f"""🗑 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻
════════════════

📌 𝗤𝘂𝗶𝘇 #{quiz_num}
❓ Question: {quiz['question']}

📍 𝗢𝗽𝘁𝗶𝗼𝗻𝘀:"""
                for i, opt in enumerate(quiz['options'], 1):
                    marker = "✅" if i-1 == quiz['correct_answer'] else "⭕"
                    confirm_text += f"\n{marker} {i}. {opt}"

                confirm_text += f"""

⚠️ 𝗧𝗼 𝗰𝗼𝗻𝗳𝗶𝗿𝗺 𝗱𝗲𝗹𝗲𝘁𝗶𝗼𝗻:
/delquiz_confirm {quiz_num}

❌ 𝗧𝗼 𝗰𝗮𝗻𝗰𝗲𝗹:
Use any other command or ignore this message
════════════════"""

                await update.message.reply_text(
                    confirm_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Sent deletion confirmation for quiz #{quiz_num}")

            except ValueError:
                await update.message.reply_text(
                    """❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗜𝗻𝗽𝘂𝘁
════════════════
Please provide a valid number.

📝 Usage:
/delquiz [quiz_number]

ℹ️ Use /editquiz to view available quizzes
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            error_msg = f"Error in delquiz command: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            await update.message.reply_text(
                """❌ 𝗘𝗿𝗿𝗼𝗿
════════════════
Failed to process delete request. Please try again later.
════════════════""",
                parse_mode=ParseMode.MARKDOWN
            )

    async def delquiz_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Confirm and execute quiz deletion - Developer only"""
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            if not context.args:
                await update.message.reply_text(
                    """❌ 𝗠𝗶𝘀𝘀𝗶𝗻𝗴 𝗤𝘂𝗶𝘇 𝗡𝘂𝗺𝗯𝗲𝗿
════════════════
Please provide the quiz number to confirm deletion.

📝 Usage:
/delquiz_confirm [quiz_number]
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            try:
                quiz_num = int(context.args[0])
                questions = self.quiz_manager.get_all_questions()

                if not (1 <= quiz_num <= len(questions)):
                    await update.message.reply_text(
                        f"""❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗤𝘂𝗶𝘇 𝗡𝘂𝗺𝗯𝗲𝗿
════════════════
Please choose a number between 1 and {len(questions)}

ℹ️ Use /editquiz to view available quizzes
════════════════""",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

                # Delete the quiz
                self.quiz_manager.delete_question(quiz_num - 1)
                remaining = len(self.quiz_manager.get_all_questions())

                await update.message.reply_text(
                    f"""✅ 𝗤𝘂𝗶𝘇 𝗗𝗲𝗹𝗲𝘁𝗲𝗱
════════════════
Successfully deleted quiz #{quiz_num}

📊 𝗦𝘁𝗮𝘁𝘀:
• Remaining quizzes: {remaining}

ℹ️ Use /editquiz to view remaining quizzes
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Successfully deleted quiz #{quiz_num}")

            except ValueError:
                await update.message.reply_text(
                    """❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗜𝗻𝗽𝘂𝘁
════════════════
Please provide a valid number.

📝 Usage:
/delquiz_confirm [quiz_number]
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            error_msg = f"Error in delquiz_confirm command: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            await update.message.reply_text(
                """❌ 𝗘𝗿𝗿𝗼𝗿
════════════════
Failed to delete quiz. Please try again.
════════════════""",
                parse_mode=ParseMode.MARKDOWN
            )

    async def totalquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show total number of quizzes - Developer only"""
        start_time = time.time()
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Log command immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/totalquiz',
                success=True
            )

            ## Force reload questions
            total_questions = len(self.quiz_manager.get_all_questions())
            logger.info(f"Total questions count: {total_questions}")

            response = f"""📊 𝗤𝘂𝗶𝘇 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀
════════════════
📚 Total Quizzes Available: {total_questions}
════════════════

Use /addquiz to add more quizzes!
Use/help to see all commands."""

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"Sent quiz count to user {update.message.from_user.id} in {response_time}ms")

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/totalquiz',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in totalquiz command: {e}\n{traceback.format_exc()}")
            await update.message.reply_text("❌ Error getting total quiz count.")

    async def send_automated_quiz(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send automated quiz to all active group chats"""
        try:
            active_chats = self.quiz_manager.get_active_chats()
            logger.info(f"Starting automated quiz broadcast to {len(active_chats)} active chats")

            for chat_id in active_chats:
                try:
                    # Check if chat is a group and bot is admin
                    chat = await context.bot.get_chat(chat_id)
                    if chat.type not in ["group", "supergroup"]:
                        logger.info(f"Skipping non-group chat {chat_id}")
                        continue

                    await self.ensure_group_registered(chat, context)

                    is_admin = await self.check_admin_status(chat_id, context)
                    if not is_admin:
                        logger.warning(f"Bot is not admin in chat {chat_id}, sending reminder")
                        await self.send_admin_reminder(chat_id, context)
                        continue

                    # Send automated quiz with tracking parameters
                    await self.send_quiz(chat_id, context, auto_sent=True, scheduled=True)
                    logger.info(f"Successfully sent automated quiz to chat {chat_id}")

                except Exception as e:
                    logger.error(f"Failed to send automated quiz to chat {chat_id}: {str(e)}\n{traceback.format_exc()}")
                    continue

            logger.info("Completed automated quiz broadcast cycle")

        except Exception as e:
            logger.error(f"Error in automated quiz broadcast: {str(e)}\n{traceback.format_exc()}")

    async def send_quiz(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, auto_sent: bool = False, scheduled: bool = False, category: str = None) -> None:
        """Send a quiz to a specific chat using native Telegram quiz format"""
        try:
            # Delete last quiz message if it exists (using database tracking)
            last_quiz_msg_id = self.db.get_last_quiz_message(chat_id)
            if last_quiz_msg_id:
                try:
                    await context.bot.delete_message(chat_id, last_quiz_msg_id)
                    logger.info(f"Deleted old quiz message {last_quiz_msg_id} in chat {chat_id}")
                    
                    # Log auto-delete activity
                    self.db.log_activity(
                        activity_type='quiz_deleted',
                        chat_id=chat_id,
                        details={
                            'auto_delete': True,
                            'old_message_id': last_quiz_msg_id
                        },
                        success=True
                    )
                except Exception as e:
                    logger.debug(f"Could not delete old quiz message: {e}")

            # Get a random question for this specific chat (with optional category filter)
            if category:
                logger.info(f"Requesting quiz from category '{category}' for chat {chat_id}")
            question = self.quiz_manager.get_random_question(chat_id, category=category)
            if not question:
                if category:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=f"❌ No questions available in the '{category}' category.\n\n"
                             f"Please try another category or contact the administrator."
                    )
                    logger.warning(f"No questions available for category '{category}' in chat {chat_id}")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="No questions available.")
                    logger.warning(f"No questions available for chat {chat_id}")
                return

            # Ensure question text is clean
            question_text = question['question'].strip()
            if question_text.startswith('/addquiz'):
                question_text = question_text[len('/addquiz'):].strip()
                logger.info(f"Cleaned /addquiz prefix from question for chat {chat_id}")

            logger.info(f"Sending quiz to chat {chat_id}. Question: {question_text[:50]}...")

            # Send the poll
            message = await context.bot.send_poll(
                chat_id=chat_id,
                question=question_text,
                options=question['options'],
                type=Poll.QUIZ,
                correct_option_id=question['correct_answer'],
                is_anonymous=False
            )

            if message and message.poll:
                # Get question ID if available
                question_id = question.get('id')
                
                poll_data = {
                    'chat_id': chat_id,
                    'correct_option_id': question['correct_answer'],
                    'user_answers': {},
                    'poll_id': message.poll.id,
                    'question': question_text,
                    'question_id': question_id,
                    'timestamp': datetime.now().isoformat()
                }
                # Store using proper poll ID key
                context.bot_data[f"poll_{message.poll.id}"] = poll_data
                logger.info(f"Stored quiz data: poll_id={message.poll.id}, chat_id={chat_id}")
                
                # Store new quiz message ID and increment quiz count
                self.db.update_last_quiz_message(chat_id, message.message_id)
                self.db.increment_quiz_count()
                
                self.command_history[chat_id].append(f"/quiz_{message.message_id}")
                
                # Get chat info for logging
                try:
                    chat = await context.bot.get_chat(chat_id)
                    chat_type = 'private' if chat.type == 'private' else 'group'
                    chat_title = chat.title if chat.type in ['group', 'supergroup'] else None
                except Exception:
                    chat_type = 'private' if chat_id > 0 else 'group'
                    chat_title = None
                
                # Log comprehensive quiz_sent activity
                self.db.log_activity(
                    activity_type='quiz_sent',
                    user_id=None,  # No specific user for quiz sending
                    chat_id=chat_id,
                    chat_title=chat_title,
                    details={
                        'question_id': question_id,
                        'question_text': question_text[:100],
                        'chat_type': chat_type,
                        'auto_sent': auto_sent,
                        'scheduled': scheduled,
                        'category': category,
                        'poll_id': message.poll.id,
                        'message_id': message.message_id
                    },
                    success=True
                )
                if category:
                    logger.info(f"Sent quiz from category '{category}' to chat {chat_id}")
                logger.info(f"Logged quiz_sent activity for chat {chat_id} (auto_sent={auto_sent}, scheduled={scheduled})")

        except Exception as e:
            logger.error(f"Error sending quiz: {str(e)}\n{traceback.format_exc()}")
            await context.bot.send_message(chat_id=chat_id, text="Error sending quiz.")

    async def _handle_quiz_not_found(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle cases where quiz data is not found"""
        await update.message.reply_text(
            """❌ 𝗤𝘂𝗶𝘇 𝗡𝗼𝘁 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲
════════════════
This quiz message is too old or no longer exists.
Please use /editquiz to view all available quizzes.
════════════════""",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.warning(f"Quiz not found in reply-to message from user {update.message.from_user.id}")

    async def _handle_invalid_quiz_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str) -> None:
        """Handle invalid quiz reply messages"""
        await update.message.reply_text(
            f"""❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗥𝗲𝗽𝗹𝘆
════════════════
Please reply to a quiz message or use:
/{command} [quiz_number]

ℹ️ Use /editquiz to view all quizzes
════════════════""",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.warning(f"Invalid quiz reply for {command} from user {update.message.from_user.id}")

    async def clear_quizzes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear all quizzes with confirmation - Developer only"""
        try:
            if not await self.is_developer(update.message.from_user.id):
                await self._handle_dev_command_unauthorized(update)
                return

            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, Clear All", callback_data="clear_quizzes_confirm_yes"),
                    InlineKeyboardButton("❌ No, Cancel", callback_data="clear_quizzes_confirm_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send confirmation message
            await update.message.reply_text(
                f"""⚠️ 𝗖𝗼𝗻𝗳𝗶𝗿𝗺 𝗤𝘂𝗶𝘇 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻
════════════════
📊 Current Questions: {len(self.quiz_manager.questions)}

⚠️ This action will:
• Delete ALL quiz questions
• Cannot be undone
• Affect all groups

Are you sure?
════════════════""",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Error in clear_quizzes: {e}")
            await update.message.reply_text("Error processing quiz deletion.")

    async def handle_clear_quizzes_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the clear quizzes confirmation callback"""
        try:
            query: CallbackQuery = update.callback_query
            await query.answer()

            if not await self.is_developer(query.from_user.id):
                await query.edit_message_text("❌ Unauthorized access.")
                return

            if query.data == "clear_quizzes_confirm_yes":
                # Clear all questions
                self.quiz_manager.questions = []
                self.quiz_manager.save_data(force=True)

                await query.edit_message_text(
                    """✅ 𝗤𝘂𝗶𝘇 𝗗𝗮𝘁𝗮 𝗖𝗹𝗲𝗮𝗿𝗲𝗱
════════════════
All quiz questions have been deleted.
Use /addquiz to add new questions.
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"All quizzes cleared by user {query.from_user.id}")

            else:  # clear_quizzes_confirm_no
                await query.edit_message_text(
                    """❌ 𝗤𝘂𝗶𝘇 𝗗𝗲𝗹𝗲𝘁𝗶𝗼𝗻 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱
════════════════
No changes were made.
════════════════""",
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            logger.error(f"Error in handle_clear_quizzes_callback: {e}")
            await query.edit_message_text("❌ Error processing quiz deletion.")
            
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show comprehensive real-time bot statistics and monitoring dashboard - OPTIMIZED with caching"""
        start_time = time.time()
        
        try:
            loading_msg = await update.message.reply_text("📊 Loading dashboard...")
            
            # OPTIMIZATION: Use cached stats if available and recent (reduces 8-10 DB queries to 0)
            current_time = datetime.now()
            cache_valid = (self._stats_cache is not None and 
                          self._stats_cache_time is not None and 
                          current_time - self._stats_cache_time < self._stats_cache_duration)
            
            if cache_valid:
                stats_data = self._stats_cache
                logger.debug("Using cached stats data (performance optimization)")
            else:
                # Fetch fresh data from database
                stats_data = {
                    'total_users': len(self.db.get_all_users_stats()),
                    'total_groups': len(self.db.get_all_groups()),
                    'active_today': self.db.get_active_users_count('today'),
                    'active_week': self.db.get_active_users_count('week'),
                    'quiz_today': self.db.get_quiz_stats_by_period('today'),
                    'quiz_week': self.db.get_quiz_stats_by_period('week'),
                    'quiz_month': self.db.get_quiz_stats_by_period('month'),
                    'quiz_all': self.db.get_quiz_stats_by_period('all'),
                    'perf_metrics': self.db.get_performance_summary(24),
                    'trending': self.db.get_trending_commands(7, 5),
                    'recent_activities': self.db.get_recent_activities(10)
                }
                # Cache the results
                self._stats_cache = stats_data
                self._stats_cache_time = current_time
                logger.debug("Stats data fetched and cached")
            
            # Extract data from cache
            total_users = stats_data['total_users']
            total_groups = stats_data['total_groups']
            active_today = stats_data['active_today']
            active_week = stats_data['active_week']
            quiz_today = stats_data['quiz_today']
            quiz_week = stats_data['quiz_week']
            quiz_month = stats_data['quiz_month']
            quiz_all = stats_data['quiz_all']
            perf_metrics = stats_data['perf_metrics']
            trending = stats_data['trending']
            recent_activities = stats_data['recent_activities']
            
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            uptime_seconds = (datetime.now() - self.bot_start_time).total_seconds()
            if uptime_seconds >= 86400:
                uptime_str = f"{uptime_seconds/86400:.1f}d"
            elif uptime_seconds >= 3600:
                uptime_str = f"{uptime_seconds/3600:.1f}h"
            else:
                uptime_str = f"{uptime_seconds/60:.1f}m"
            
            activity_feed = ""
            for activity in recent_activities[:10]:
                time_ago = self.db.format_relative_time(activity['timestamp'])
                activity_type = activity['activity_type']
                username = activity.get('username', 'Unknown')
                
                if activity_type == 'command':
                    details = activity.get('details', {})
                    cmd = details.get('command', 'unknown') if isinstance(details, dict) else 'unknown'
                    activity_feed += f"• {time_ago}: @{username} used /{cmd}\n"
                elif activity_type == 'quiz_sent':
                    activity_feed += f"• {time_ago}: Quiz sent to group\n"
                elif activity_type == 'quiz_answered':
                    activity_feed += f"• {time_ago}: @{username} answered quiz\n"
                else:
                    activity_feed += f"• {time_ago}: {activity_type}\n"
            
            if not activity_feed:
                activity_feed = "• No recent activity\n"
            
            trending_text = ""
            for i, cmd in enumerate(trending[:5], 1):
                trending_text += f"{i}. /{cmd['command']}: {cmd['count']}x\n"
            if not trending_text:
                trending_text = "No commands used yet\n"
            
            stats_message = f"""📊 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘀
━━━━━━━━━━━━━━━━━━━━
• 🌐 Total Groups: {total_groups:,}
• 👥 Total Users: {total_users:,}

════════════════════
🤖 𝗢𝘃𝗲𝗿𝗮𝗹𝗹 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲
────────────────────
• Today: {quiz_today['quizzes_sent']:,}
• This Week: {quiz_week['quizzes_sent']:,}
• This Month: {quiz_month['quizzes_sent']:,}
• Total: {quiz_all['quizzes_sent']:,}

━━━━━━━━━━━━━━━━━━━━
✨ Keep quizzing & growing! 🚀"""
            
            await loading_msg.edit_text(stats_message)
            
            logger.info(f"Showed stats to user {update.effective_user.id} in {(time.time() - start_time)*1000:.0f}ms")
            
        except Exception as e:
            logger.error(f"Error in stats_command: {e}", exc_info=True)
            await update.message.reply_text("❌ Error loading dashboard. Please try again.")
            
    async def handle_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from start command buttons"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Route to appropriate handler based on callback data
            if query.data == "start_quiz":
                # Start a quiz
                await self.send_quiz(query.message.chat.id, context)
                await query.answer("🎯 Quiz started!", show_alert=False)
                
            elif query.data == "my_stats":
                # Show user stats
                user_id = query.from_user.id
                stats = self.quiz_manager.get_user_stats(user_id)
                
                if stats:
                    stats_message = f"""📊 𝗬𝗼𝘂𝗿 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲 𝗦𝘁𝗮𝘁𝘀
━━━━━━━━━━━━━━━━━━━━━

💯 Total Score: {stats['score']} points
✅ Total Quizzes: {stats['total_attempts']}
🎯 Correct Answers: {stats['correct_answers']}
📊 Accuracy: {stats['accuracy']}%
🔥 Current Streak: {stats['current_streak']}
👑 Best Streak: {stats['longest_streak']}

━━━━━━━━━━━━━━━━━━━━━
💡 Keep going to improve your rank!"""
                else:
                    stats_message = """📊 𝗬𝗼𝘂𝗿 𝗣𝗲𝗿𝗳𝗼𝗿𝗺𝗮𝗻𝗰𝗲 𝗦𝘁𝗮𝘁𝘀
━━━━━━━━━━━━━━━━━━━━━

🎯 No stats yet!
Start playing quizzes to track your progress.

━━━━━━━━━━━━━━━━━━━━━
💡 Use the button below to start!"""
                
                keyboard = [[InlineKeyboardButton("🎯 Start Quiz Now", callback_data="start_quiz")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(stats_message, reply_markup=reply_markup)
                
            elif query.data == "leaderboard":
                # Show leaderboard
                leaderboard = self.quiz_manager.get_leaderboard()
                
                leaderboard_text = """╔═══════════════════════╗
║  🏆 𝗚𝗹𝗼𝗯𝗮𝗹 𝗟𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱  ║
╚═══════════════════════╝

✨ 𝗧𝗼𝗽 𝟱 𝗤𝘂𝗶𝘇 𝗖𝗵𝗮𝗺𝗽𝗶𝗼𝗻𝘀 ✨
━━━━━━━━━━━━━━━━━━━━━━━"""
                
                if not leaderboard:
                    leaderboard_text += "\n\n🎯 No champions yet!\n💡 Be the first to claim the throne!"
                else:
                    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                    for rank, entry in enumerate(leaderboard[:5], 1):
                        try:
                            user = await context.bot.get_chat(entry['user_id'])
                            username = user.first_name or user.username or "Anonymous"
                            if len(username) > 15:
                                username = username[:12] + "..."
                            
                            score_display = f"{entry['score']/1000:.1f}K" if entry['score'] >= 1000 else str(entry['score'])
                            leaderboard_text += f"\n\n{medals[rank-1]} {username}\n💯 {score_display} pts • 🎯 {entry['accuracy']}%"
                        except:
                            continue
                    
                    leaderboard_text += "\n\n━━━━━━━━━━━━━━━━━━━━━━━\n💡 Use /leaderboard for full list"
                
                keyboard = [[InlineKeyboardButton("🎯 Start Quiz", callback_data="start_quiz")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(leaderboard_text, reply_markup=reply_markup)
                
            elif query.data == "help":
                # Show help
                help_message = """❓ 𝗛𝗲𝗹𝗽 & 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀
━━━━━━━━━━━━━━━━━━━━━━

📌 𝗕𝗮𝘀𝗶𝗰 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀:
/start - Start the bot
/quiz - Get a new quiz
/mystats - View your stats
/leaderboard - See top players
/help - Show this help

🎯 𝗛𝗼𝘄 𝘁𝗼 𝗣𝗹𝗮𝘆:
1. Click "Start Quiz" or use /quiz
2. Answer the question
3. Earn points for correct answers
4. Build your streak for bonus points
5. Climb the leaderboard!

💡 𝗧𝗶𝗽𝘀:
• Maintain streaks for extra points
• Check leaderboard to see your rank
• Add bot to groups for auto-quizzes
• Answer quickly for the best experience

━━━━━━━━━━━━━━━━━━━━━━
🚀 Ready to play? Start now!"""
                
                keyboard = [[InlineKeyboardButton("🎯 Start Quiz", callback_data="start_quiz")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(help_message, reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error in start callback handler: {e}")
            await query.answer("❌ Error processing request", show_alert=True)
    
    async def handle_category_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from category selection buttons"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Extract category name from callback data (format: "cat_CategoryName")
            category_name = query.data.replace("cat_", "")
            
            logger.info(f"User {query.from_user.id} selected category: {category_name}")
            
            # Get user info for display
            user = query.from_user
            user_link = f"[{user.first_name}](tg://user?id={user.id})"
            
            # Check if we have questions available
            total_questions = len(self.quiz_manager.questions)
            
            if total_questions == 0:
                await query.message.reply_text(
                    f"❌ No quiz questions available yet.\n\n"
                    f"Please contact the administrator to add questions.",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.warning(f"No questions available for category {category_name}")
                return
            
            # Send a confirmation message with the category
            category_emoji = {
                "General Knowledge": "🌍",
                "Current Affairs": "📰",
                "Static GK": "📚",
                "Science & Technology": "🔬",
                "History": "📜",
                "Geography": "🗺",
                "Economics": "💰",
                "Political Science": "🏛",
                "Constitution": "📖",
                "Constitution & Law": "⚖",
                "Arts & Literature": "🎭",
                "Sports & Games": "🎮"
            }
            
            emoji = category_emoji.get(category_name, "📚")
            
            # Send a quiz from the selected category
            await query.message.reply_text(
                f"{emoji} **{category_name}** Category Selected!\n\n"
                f"👤 {user_link} requested a quiz\n"
                f"⏰ Get ready for your question...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send the quiz to the chat with category filter
            await self.send_quiz(query.message.chat.id, context, auto_sent=False, scheduled=False, category=category_name)
            
            # Log the category selection activity
            self.db.log_activity(
                activity_type='category_selected',
                user_id=user.id,
                chat_id=query.message.chat.id,
                username=user.username,
                command='/category',
                details={
                    'category': category_name,
                    'emoji': emoji
                },
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error in category callback handler: {e}")
            await query.answer("❌ Error processing category selection", show_alert=True)
    
    async def handle_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from the stats dashboard"""
        query = update.callback_query
        await query.answer()
        
        try:
            start_time = time.time()
            
            if query.data == "stats_refresh":
                await query.edit_message_text("🔄 Refreshing dashboard...")
                
                total_users = len(self.db.get_all_users_stats())
                total_groups = len(self.db.get_all_groups())
                active_today = self.db.get_active_users_count('today')
                active_week = self.db.get_active_users_count('week')
                
                quiz_today = self.db.get_quiz_stats_by_period('today')
                quiz_week = self.db.get_quiz_stats_by_period('week')
                quiz_month = self.db.get_quiz_stats_by_period('month')
                quiz_all = self.db.get_quiz_stats_by_period('all')
                
                perf_metrics = self.db.get_performance_summary(24)
                trending = self.db.get_trending_commands(7, 5)
                recent_activities = self.db.get_recent_activities(10)
                
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                uptime_seconds = (datetime.now() - self.bot_start_time).total_seconds()
                if uptime_seconds >= 86400:
                    uptime_str = f"{uptime_seconds/86400:.1f}d"
                elif uptime_seconds >= 3600:
                    uptime_str = f"{uptime_seconds/3600:.1f}h"
                else:
                    uptime_str = f"{uptime_seconds/60:.1f}m"
                
                activity_feed = ""
                for activity in recent_activities[:10]:
                    time_ago = self.db.format_relative_time(activity['timestamp'])
                    activity_type = activity['activity_type']
                    username = activity.get('username', 'Unknown')
                    
                    if activity_type == 'command':
                        details = activity.get('details', {})
                        cmd = details.get('command', 'unknown') if isinstance(details, dict) else 'unknown'
                        activity_feed += f"• {time_ago}: @{username} used /{cmd}\n"
                    elif activity_type == 'quiz_sent':
                        activity_feed += f"• {time_ago}: Quiz sent to group\n"
                    elif activity_type == 'quiz_answered':
                        activity_feed += f"• {time_ago}: @{username} answered quiz\n"
                    else:
                        activity_feed += f"• {time_ago}: {activity_type}\n"
                
                if not activity_feed:
                    activity_feed = "• No recent activity\n"
                
                trending_text = ""
                for i, cmd in enumerate(trending[:5], 1):
                    trending_text += f"{i}. /{cmd['command']}: {cmd['count']}x\n"
                if not trending_text:
                    trending_text = "No commands used yet\n"
                
                stats_message = f"""📊 Real-Time Dashboard
━━━━━━━━━━━━━━━━━━━

👥 User Engagement
• Total Users: {total_users:,}
• Active Today: {active_today}
• Active This Week: {active_week}

📝 Quiz Activity (Today/Week/Month/All)
• Quizzes Sent: {quiz_today['quizzes_sent']}/{quiz_week['quizzes_sent']}/{quiz_month['quizzes_sent']}/{quiz_all['quizzes_sent']}
• Success Rate: {quiz_all['success_rate']}%

📊 Groups
• Total Groups: {total_groups:,}

⚡ Performance (24h)
• Avg Response Time: {perf_metrics['avg_response_time']:.0f}ms
• Commands Executed: {perf_metrics['total_api_calls']:,}
• Error Rate: {perf_metrics['error_rate']:.1f}%
• Memory Usage: {memory_mb:.1f}MB

🔥 Trending Commands (7d)
{trending_text}
📜 Recent Activity
{activity_feed}
━━━━━━━━━━━━━━━━━━━
⚙️ Uptime: {uptime_str} | 🕐 Load: {(time.time() - start_time)*1000:.0f}ms"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="stats_refresh"),
                        InlineKeyboardButton("📊 Activity", callback_data="stats_activity")
                    ],
                    [
                        InlineKeyboardButton("⚡ Performance", callback_data="stats_performance"),
                        InlineKeyboardButton("📈 Trends", callback_data="stats_trends")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    stats_message,
                    reply_markup=reply_markup
                )
                
            elif query.data == "stats_activity":
                recent_activities = self.db.get_recent_activities(25)
                activity_text = "📊 Recent Activity Feed\n━━━━━━━━━━━━━━━━━━━\n\n"
                
                for activity in recent_activities:
                    time_ago = self.db.format_relative_time(activity['timestamp'])
                    activity_type = activity['activity_type']
                    username = activity.get('username', 'Unknown')
                    
                    if activity_type == 'command':
                        details = activity.get('details', {})
                        cmd = details.get('command', 'unknown') if isinstance(details, dict) else 'unknown'
                        activity_text += f"[{time_ago}] @{username}: /{cmd}\n"
                    elif activity_type == 'quiz_sent':
                        activity_text += f"[{time_ago}] Quiz sent\n"
                    elif activity_type == 'quiz_answered':
                        details = activity.get('details', {})
                        correct = details.get('is_correct', False) if isinstance(details, dict) else False
                        emoji = "✅" if correct else "❌"
                        activity_text += f"[{time_ago}] {emoji} @{username} answered\n"
                    else:
                        activity_text += f"[{time_ago}] {activity_type}\n"
                
                activity_text += "\n━━━━━━━━━━━━━━━━━━━"
                
                keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="stats_refresh")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    activity_text,
                    reply_markup=reply_markup
                )
                
            elif query.data == "stats_performance":
                perf_metrics = self.db.get_performance_summary(24)
                
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                perf_text = f"""⚡ Performance Metrics (24h)
━━━━━━━━━━━━━━━━━━━

📈 Response Times
• Average: {perf_metrics['avg_response_time']:.2f}ms
• Total API Calls: {perf_metrics['total_api_calls']:,}

💾 Memory Usage
• Current: {memory_mb:.2f} MB
• Average: {perf_metrics['avg_memory_mb']:.2f} MB

❌ Error Rate
• Rate: {perf_metrics['error_rate']:.2f}%

🟢 Uptime
• Status: {perf_metrics['uptime_percent']:.1f}%

━━━━━━━━━━━━━━━━━━━"""
                
                keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="stats_refresh")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    perf_text,
                    reply_markup=reply_markup
                )
                
            elif query.data == "stats_trends":
                trending = self.db.get_trending_commands(7, 10)
                activity_stats = self.db.get_activity_stats(7)
                
                trends_text = "📈 Trends & Analytics (7d)\n━━━━━━━━━━━━━━━━━━━\n\n"
                trends_text += "🔥 Trending Commands\n"
                for i, cmd in enumerate(trending, 1):
                    trends_text += f"{i}. /{cmd['command']}: {cmd['count']}x\n"
                
                trends_text += f"\n📊 Activity Breakdown\n"
                for activity_type, count in activity_stats['activities_by_type'].items():
                    trends_text += f"• {activity_type}: {count:,}\n"
                
                trends_text += f"\n✅ Success Rate: {activity_stats['success_rate']:.1f}%\n"
                trends_text += f"⚡ Avg Response: {activity_stats['avg_response_time_ms']:.0f}ms\n"
                trends_text += "\n━━━━━━━━━━━━━━━━━━━"
                
                keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="stats_refresh")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    trends_text,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in handle_stats_callback: {e}", exc_info=True)
            await query.edit_message_text("❌ Error processing stats. Please try again.")
    
    async def handle_devstats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from devstats dashboard"""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "devstats_refresh":
                await query.edit_message_text("🔄 Refreshing dev stats...")
                
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if hasattr(self, 'bot_start_time'):
                    uptime_seconds = (datetime.now() - self.bot_start_time).total_seconds()
                else:
                    uptime_seconds = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
                
                if uptime_seconds >= 86400:
                    uptime_str = f"{uptime_seconds/86400:.1f} days"
                elif uptime_seconds >= 3600:
                    uptime_str = f"{uptime_seconds/3600:.1f} hours"
                else:
                    uptime_str = f"{uptime_seconds/60:.1f} minutes"
                
                perf_24h = self.db.get_performance_summary(24)
                activity_stats = self.db.get_activity_stats(1)
                
                total_users = len(self.db.get_all_users_stats())
                active_today = self.db.get_active_users_count('today')
                active_week = self.db.get_active_users_count('week')
                active_month = self.db.get_active_users_count('month')
                
                new_users = len(self.db.get_new_users(7))
                most_active = self.db.get_most_active_users(5, 30)
                
                quiz_today = self.db.get_quiz_stats_by_period('today')
                quiz_week = self.db.get_quiz_stats_by_period('week')
                
                commands_24h = activity_stats['activities_by_type'].get('command', 0)
                quizzes_sent_24h = activity_stats['activities_by_type'].get('quiz_sent', 0)
                quizzes_answered_24h = activity_stats['activities_by_type'].get('quiz_answered', 0)
                broadcasts_24h = activity_stats['activities_by_type'].get('broadcast', 0)
                errors_24h = activity_stats['activities_by_type'].get('error', 0)
                
                recent_activities = self.db.get_recent_activities(10)
                activity_feed = ""
                for activity in recent_activities:
                    time_ago = self.db.format_relative_time(activity['timestamp'])
                    activity_type = activity['activity_type']
                    username = activity.get('username', 'Unknown')
                    
                    if activity_type == 'command':
                        details = activity.get('details', {})
                        cmd = details.get('command', 'unknown') if isinstance(details, dict) else 'unknown'
                        activity_feed += f"• {time_ago}: @{username} /{cmd}\n"
                    elif activity_type == 'quiz_sent':
                        activity_feed += f"• {time_ago}: Quiz sent\n"
                    elif activity_type == 'quiz_answered':
                        activity_feed += f"• {time_ago}: @{username} answered\n"
                    else:
                        activity_feed += f"• {time_ago}: {activity_type}\n"
                
                if not activity_feed:
                    activity_feed = "No recent activity"
                
                most_active_text = ""
                for i, user in enumerate(most_active[:5], 1):
                    name = user.get('first_name') or user.get('username') or f"User{user['user_id']}"
                    most_active_text += f"{i}. {name}: {user['activity_count']} actions\n"
                if not most_active_text:
                    most_active_text = "No active users yet"
                
                devstats_message = f"""📊 **Developer Statistics Dashboard**
━━━━━━━━━━━━━━━━━━━

⚙️ **System Health**
• Uptime: {uptime_str}
• Memory: {memory_mb:.1f} MB (avg: {perf_24h['avg_memory_mb']:.1f} MB)
• Error Rate: {perf_24h['error_rate']:.1f}%
• Avg Response: {perf_24h['avg_response_time']:.0f}ms

📊 **Activity Breakdown** (Last 24h)
• Commands Executed: {commands_24h:,}
• Quizzes Sent: {quizzes_sent_24h:,}
• Quizzes Answered: {quizzes_answered_24h:,}
• Broadcasts Sent: {broadcasts_24h:,}
• Errors Logged: {errors_24h:,}

👥 **User Engagement**
• Total Users: {total_users:,}
• Active Today: {active_today}
• Active This Week: {active_week}
• Active This Month: {active_month}
• New Users (7d): {new_users}

📝 **Quiz Performance**
• Sent Today: {quiz_today['quizzes_sent']}
• Sent This Week: {quiz_week['quizzes_sent']}
• Success Rate: {quiz_week['success_rate']}%

🏆 **Most Active Users** (30d)
{most_active_text}

📜 **Recent Activity Feed**
{activity_feed}

━━━━━━━━━━━━━━━━━━━"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data="devstats_refresh")],
                    [
                        InlineKeyboardButton("📊 Full Activity", callback_data="devstats_activity"),
                        InlineKeyboardButton("⚡ Performance", callback_data="devstats_performance")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    devstats_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                
            elif query.data == "devstats_activity":
                recent_activities = self.db.get_recent_activities(50)
                activity_text = "📜 **Full Activity Stream**\n━━━━━━━━━━━━━━━━━━━\n\n"
                
                for activity in recent_activities:
                    time_ago = self.db.format_relative_time(activity['timestamp'])
                    activity_type = activity['activity_type']
                    username = activity.get('username', 'Unknown')
                    
                    if activity_type == 'command':
                        details = activity.get('details', {})
                        cmd = details.get('command', 'unknown') if isinstance(details, dict) else 'unknown'
                        activity_text += f"[{time_ago}] @{username}: /{cmd}\n"
                    elif activity_type == 'quiz_sent':
                        activity_text += f"[{time_ago}] Quiz sent\n"
                    elif activity_type == 'quiz_answered':
                        details = activity.get('details', {})
                        correct = details.get('is_correct', False) if isinstance(details, dict) else False
                        emoji = "✅" if correct else "❌"
                        activity_text += f"[{time_ago}] {emoji} @{username} answered\n"
                    else:
                        activity_text += f"[{time_ago}] {activity_type}\n"
                
                activity_text += "\n━━━━━━━━━━━━━━━━━━━"
                
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="devstats_refresh")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    activity_text,
                    reply_markup=reply_markup
                )
                
            elif query.data == "devstats_performance":
                perf_metrics = self.db.get_performance_summary(24)
                
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                perf_text = f"""⚡ **Performance Details** (24h)
━━━━━━━━━━━━━━━━━━━

📈 **Response Times**
• Average: {perf_metrics['avg_response_time']:.2f}ms
• Total API Calls: {perf_metrics['total_api_calls']:,}

💾 **Memory Usage**
• Current: {memory_mb:.2f} MB
• Average: {perf_metrics['avg_memory_mb']:.2f} MB

❌ **Error Rate**
• Rate: {perf_metrics['error_rate']:.2f}%

🟢 **Uptime**
• Status: {perf_metrics['uptime_percent']:.1f}%

━━━━━━━━━━━━━━━━━━━"""
                
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="devstats_refresh")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    perf_text,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in handle_devstats_callback: {e}", exc_info=True)
            await query.edit_message_text("❌ Error processing devstats. Please try again.")
    
    async def handle_activity_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callbacks from activity stream"""
        query = update.callback_query
        await query.answer()
        
        try:
            activity_type = 'all'
            
            if query.data.startswith("activity_refresh_"):
                activity_type = query.data.replace("activity_refresh_", "")
            elif query.data == "activity_all":
                activity_type = 'all'
            elif query.data.startswith("activity_"):
                activity_type = query.data.replace("activity_", "")
            
            await query.edit_message_text(f"📜 Loading activity stream ({activity_type})...")
            
            if activity_type == 'all':
                activities = self.db.get_recent_activities(50)
            else:
                activities = self.db.get_recent_activities(50, activity_type)
            
            activity_text = f"""📜 **Live Activity Stream**
Type: {activity_type.upper()}
━━━━━━━━━━━━━━━━━━━

"""
            
            for activity in activities[:50]:
                time_ago = self.db.format_relative_time(activity['timestamp'])
                activity_type_str = activity['activity_type']
                username = activity.get('username', 'Unknown')
                chat_title = activity.get('chat_title', '')
                
                details = activity.get('details', {})
                if isinstance(details, dict):
                    if activity_type_str == 'command':
                        cmd = details.get('command', 'unknown')
                        activity_text += f"[{time_ago}] @{username}: /{cmd}\n"
                    elif activity_type_str == 'quiz_sent':
                        if chat_title:
                            activity_text += f"[{time_ago}] Quiz sent to {chat_title}\n"
                        else:
                            activity_text += f"[{time_ago}] Quiz sent\n"
                    elif activity_type_str == 'quiz_answered':
                        correct = details.get('is_correct', False)
                        emoji = "✅" if correct else "❌"
                        activity_text += f"[{time_ago}] {emoji} @{username} answered\n"
                    elif activity_type_str == 'broadcast':
                        recipients = details.get('total_recipients', 0)
                        activity_text += f"[{time_ago}] Broadcast to {recipients} recipients\n"
                    elif activity_type_str == 'error':
                        error_msg = details.get('error', 'Unknown error')[:50]
                        activity_text += f"[{time_ago}] ❌ Error: {error_msg}\n"
                    else:
                        activity_text += f"[{time_ago}] {activity_type_str}\n"
                else:
                    activity_text += f"[{time_ago}] {activity_type_str}\n"
            
            activity_text += f"""
━━━━━━━━━━━━━━━━━━━
📊 Showing {len(activities[:50])} activities"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"activity_refresh_{activity_type}"),
                    InlineKeyboardButton("🔙 All Types", callback_data="activity_all")
                ],
                [
                    InlineKeyboardButton("💬 Commands", callback_data="activity_command"),
                    InlineKeyboardButton("📝 Quizzes", callback_data="activity_quiz_sent")
                ],
                [
                    InlineKeyboardButton("✅ Answers", callback_data="activity_quiz_answered"),
                    InlineKeyboardButton("❌ Errors", callback_data="activity_error")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                activity_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in handle_activity_callback: {e}", exc_info=True)
            await query.edit_message_text("❌ Error processing activity. Please try again.")
                
    async def _show_detailed_user_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed user statistics"""
        try:
            # Get user stats
            if not hasattr(self.quiz_manager, 'stats') or not self.quiz_manager.stats:
                await query.edit_message_text(
                    "❌ No user statistics available.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
                )
                return
                
            valid_stats = {k: v for k, v in self.quiz_manager.stats.items() 
                         if isinstance(v, dict) and 'total_quizzes' in v}
                
            if not valid_stats:
                await query.edit_message_text(
                    "❌ No valid user statistics available.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
                )
                return
                
            # Sort users by score
            sorted_users = sorted(
                valid_stats.items(), 
                key=lambda x: x[1].get('current_score', 0), 
                reverse=True
            )
            
            # Format detailed user stats
            stats_message = """👥 Detailed User Statistics
━━━━━━━━━━━━━━━━━━━━━━━

🏆 Top Users by Score:
"""
            
            # Add top 10 users (or all if less than 10)
            for i, (user_id, stats) in enumerate(sorted_users[:10], 1):
                score = stats.get('current_score', 0)
                success_rate = stats.get('success_rate', 0)
                total_quizzes = stats.get('total_quizzes', 0)
                
                stats_message += f"{i}. User {user_id}: {score} pts ({success_rate}% success, {total_quizzes} quizzes)\n"
                
            stats_message += "\n📊 𝐔𝐬𝐞𝐫 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬 𝐒𝐮𝐦𝐦𝐚𝐫𝐲:\n"
            
            # Count users by activity
            current_date = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
            month_start = (datetime.now().replace(day=1)).strftime('%Y-%m-%d')
            
            active_today = sum(1 for stats in valid_stats.values() if stats.get('last_activity_date') == current_date)
            active_week = sum(1 for stats in valid_stats.values() if stats.get('last_activity_date', '') >= week_start)
            active_month = sum(1 for stats in valid_stats.values() if stats.get('last_activity_date', '') >= month_start)
            
            stats_message += f"• Total Users: {len(valid_stats)}\n"
            stats_message += f"• Active Today: {active_today}\n"
            stats_message += f"• Active This Week: {active_week}\n"
            stats_message += f"• Active This Month: {active_month}\n"
            
            # Add navigation button
            back_button = InlineKeyboardButton("« Back to Main Stats", callback_data="refresh_stats")
            reply_markup = InlineKeyboardMarkup([[back_button]])
            
            await query.edit_message_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in _show_detailed_user_stats: {e}")
            await query.edit_message_text(
                "❌ Error processing user statistics.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
            )
            
    async def _show_detailed_group_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed group statistics"""
        try:
            # Get active groups
            active_chats = self.quiz_manager.get_active_chats() if hasattr(self.quiz_manager, 'get_active_chats') else []
            
            if not active_chats:
                await query.edit_message_text(
                    "❌ No group statistics available.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
                )
                return
                
            # Format detailed group stats
            stats_message = """👥 Detailed Group Statistics
━━━━━━━━━━━━━━━━━━━━━━━

📊 Active Groups:
"""
            
            # Get activity dates for each group
            group_data = []
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            for chat_id in active_chats:
                try:
                    # Get last activity
                    last_activity = "Unknown"
                    if hasattr(self.quiz_manager, 'get_group_last_activity'):
                        last_activity = self.quiz_manager.get_group_last_activity(chat_id) or "Never"
                        
                    # Get group members count if available
                    members_count = 0
                    if hasattr(self.quiz_manager, 'get_group_members'):
                        members = self.quiz_manager.get_group_members(chat_id)
                        if members:
                            members_count = len(members)
                            
                    # Determine activity status
                    status = "🔴 Inactive"
                    if last_activity == current_date:
                        status = "🟢 Active Today"
                    elif last_activity != "Never":
                        status = "🟠 Recent Activity"
                        
                    group_data.append((chat_id, last_activity, members_count, status))
                except Exception:
                    continue
                    
            # Sort groups by activity (most recent first)
            group_data.sort(key=lambda x: x[1] == current_date, reverse=True)
            
            # Add group listings
            for chat_id, last_activity, members_count, status in group_data:
                stats_message += f"• Group {chat_id}: {status}\n"
                stats_message += f"  └ Members: {members_count}, Last Activity: {last_activity}\n"
                
            # Add summary
            active_today = sum(1 for _, last_activity, _, _ in group_data if last_activity == current_date)
            
            stats_message += f"\n📊 𝐒𝐮𝐦𝐦𝐚𝐫𝐲:\n"
            stats_message += f"• Total Groups: {len(active_chats)}\n"
            stats_message += f"• Active Today: {active_today}\n"
            
            # Add navigation button
            back_button = InlineKeyboardButton("« Back to Main Stats", callback_data="refresh_stats")
            reply_markup = InlineKeyboardMarkup([[back_button]])
            
            await query.edit_message_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in _show_detailed_group_stats: {e}")
            await query.edit_message_text(
                "❌ Error processing group statistics.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
            )
            
    async def _show_detailed_system_stats(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show detailed system statistics"""
        try:
            # Get system metrics
            process = psutil.Process()
            
            # CPU usage (overall system and this process)
            cpu_percent = process.cpu_percent(interval=0.1)
            system_cpu = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024  # MB
            virtual_memory = psutil.virtual_memory()
            system_memory_usage = virtual_memory.percent
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            disk_free_gb = disk_usage.free / (1024 ** 3)  # GB
            
            # Network stats - can be complex, simplified here
            net_io = psutil.net_io_counters()
            bytes_sent_mb = net_io.bytes_sent / (1024 ** 2)  # MB
            bytes_recv_mb = net_io.bytes_recv / (1024 ** 2)  # MB
            
            # Bot uptime
            uptime_seconds = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds()
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            uptime_str = ""
            if days > 0:
                uptime_str += f"{int(days)}d "
            if hours > 0 or days > 0:
                uptime_str += f"{int(hours)}h "
            if minutes > 0 or hours > 0 or days > 0:
                uptime_str += f"{int(minutes)}m "
            uptime_str += f"{int(seconds)}s"
            
            # Questions database info
            total_questions = 0
            if hasattr(self.quiz_manager, 'questions'):
                if isinstance(self.quiz_manager.questions, list):
                    total_questions = len(self.quiz_manager.questions)
                    
            # Create detailed system stats message piece by piece
            divider = "━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Start with header
            stats_message = f"⚙️ Detailed System Statistics\n{divider}\n\n"
            
            # System resources section
            stats_message += "🖥️ System Resources:\n"
            stats_message += f"• CPU Usage (Bot): {cpu_percent:.1f}%\n"
            stats_message += f"• CPU Usage (System): {system_cpu:.1f}%\n"
            stats_message += f"• Memory Usage (Bot): {memory_usage_mb:.1f}MB\n"
            stats_message += f"• Memory Usage (System): {system_memory_usage:.1f}%\n"
            stats_message += f"• Disk Usage: {disk_percent:.1f}% (Free: {disk_free_gb:.1f}GB)\n"
            stats_message += f"• Network I/O: {bytes_sent_mb:.1f}MB sent, {bytes_recv_mb:.1f}MB received\n\n"
            
            # Uptime & availability section
            stats_message += "⏱️ Uptime & Availability:\n"
            stats_message += f"• Bot Uptime: {uptime_str}\n"
            stats_message += f"• Start Time: {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}\n"
            stats_message += f"• Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Database status section
            stats_message += "📊 Database Status:\n"
            stats_message += f"• Questions: {total_questions} entries\n"
            stats_message += "• Database Health: ✅ Operational\n\n"
            
            # System environment section
            stats_message += "🔄 System Environment:\n"
            stats_message += f"• Python Version: {sys.version.split()[0]}\n"
            stats_message += f"• Platform: {sys.platform}\n"
            stats_message += f"• Process PID: {process.pid}"
            
            # Add navigation button
            back_button = InlineKeyboardButton("« Back to Main Stats", callback_data="refresh_stats")
            reply_markup = InlineKeyboardMarkup([[back_button]])
            
            await query.edit_message_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in _show_detailed_system_stats: {e}")
            await query.edit_message_text(
                "❌ Error processing system statistics.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data="refresh_stats")]])
            )

    async def setup_bot(quiz_manager):
        """Setup and start the Telegram bot"""
        logger.info("Setting up Telegram bot...")
        try:
            bot = TelegramQuizBot(quiz_manager)
            token = os.environ.get("TELEGRAM_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_TOKEN environment variable is required")
            await bot.initialize(token)
            return bot    
        except Exception as e:
            logger.error(f"Failed to setup Telegram bot: {e}")
            raise

    def extract_status_change(chat_member_update):
        """Extract whetherbot was added or removed."""
        try:
            if not chat_member_update or not hasattr(chat_member_update, 'difference'):
                return None

            status_change = chat_member_update.difference().get("status")
            if status_change is None:
                return None

            old_status = chat_member_update.old_chat_member.status
            new_status = chat_member_update.new_chat_member.status

            was_member = old_status in ["member", "administrator", "creator"]
            is_member = new_status in ["member", "administrator", "creator"]

            return was_member, is_member
        except Exception as e:
            logger.error(f"Error in extract_status_change: {e}")
            return None

    async def setup_bot(quiz_manager):
        """Setup and start the Telegram bot"""
        logger.info("Setting up Telegram bot...")
        try:
            bot = TelegramQuizBot(quiz_manager)
            token = os.environ.get("TELEGRAM_TOKEN")
            if not token:
                raise ValueError("TELEGRAM_TOKEN environment variable is required")
            await bot.initialize(token)
            return bot    
        except Exception as e:
            logger.error(f"Failed to setup Telegram bot: {e}")
            raise

    async def cleanup_old_messages(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clean up old messages from the chat - Disabled (get_chat_history not available)"""
        # NOTE: get_chat_history() is not available in python-telegram-bot
        # Message cleanup is handled via other mechanisms (auto-delete after quiz completion)
        logger.debug(f"Message cleanup skipped for chat {chat_id} - handled by auto-delete mechanisms")

    async def send_automated_quiz(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send automated quiz to all active groups"""
        try:
            active_chats = self.quiz_manager.get_active_chats()
            for chat_id in active_chats:
                try:
                    # Check if bot is admin
                    is_admin = await self.check_admin_status(chat_id, context)

                    if is_admin:
                        # Delete previous quiz if exists
                        try:
                            chat_history = self.command_history.get(chat_id, [])
                            if chat_history:
                                last_quiz = next((cmd for cmd in reversed(chat_history) if cmd.startswith("/quiz_")), None)
                                if last_quiz:
                                    msg_id = int(last_quiz.split("_")[1])
                                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                    logger.info(f"Deleted previous quiz in chat {chat_id}")
                        except Exception as e:
                            logger.warning(f"Failed to delete previous quiz: {e}")

                        # Send new quiz with tracking parameters
                        await self.send_quiz(chat_id, context, auto_sent=True, scheduled=True)
                        logger.info(f"Sent automated quiz to chat {chat_id}")
                    else:
                        # Send admin reminder if not admin
                        await self.send_admin_reminder(chat_id, context)
                        logger.info(f"Sent admin reminder to chat {chat_id}")

                except Exception as e:
                    logger.error(f"Error processing chat {chat_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in automated quiz: {e}")

    async def track_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enhanced tracking when bot is added to or removed from chats"""
        try:
            chat = update.effective_chat
            if not chat:
                return

            result = self.extract_status_change(update.my_chat_member)
            if result is None:
                return

            was_member, is_member = result

            if chat.type in ["group", "supergroup"]:
                if not was_member and is_member:
                    # Bot was added to a group
                    self.quiz_manager.add_active_chat(chat.id)
                    await self.ensure_group_registered(chat, context)
                    await self.send_welcome_message(chat.id, context)

                    # Schedule first quiz delivery (auto-sent when bot joins)
                    if await self.check_admin_status(chat.id, context):
                        await self.send_quiz(chat.id, context, auto_sent=True, scheduled=False)
                    else:
                        await self.send_admin_reminder(chat.id, context)

                    logger.info(f"Bot added to group {chat.title} ({chat.id})")

                elif was_member and not is_member:
                    # Bot was removed from a group
                    self.quiz_manager.remove_active_chat(chat.id)
                    logger.info(f"Bot removed from group {chat.title} ({chat.id})")

        except Exception as e:
            logger.error(f"Error in track_chats: {e}")

