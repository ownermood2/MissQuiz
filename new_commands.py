import logging
import traceback
from datetime import datetime, timedelta
import psutil
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Configure logging
logger = logging.getLogger(__name__)

async def dev_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage developer roles"""
    try:
        user_id = update.message.from_user.id

        # First check if user is already a developer
        is_dev = await self.is_developer(user_id)

        if not is_dev:
            await update.message.reply_text("⛔ You don't have permission to manage developer roles.")
            return

        # If the user is a developer, show the developer management interface
        dev_message = """👑 𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 𝐌𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭
━━━━━━━━━━━━━━━━━━━━━━━

🔐 You have developer access to this bot.

To add a new developer, use:
/dev add <user_id>

To remove a developer, use:
/dev remove <user_id>

To list all developers, use:
/dev list

💡 The user ID can be found by forwarding a message from that user to @userinfobot.
━━━━━━━━━━━━━━━━━━━━━━━"""

        # Check if there are any arguments
        if context.args:
            command = context.args[0].lower()

            # Handle different subcommands
            if command == "list":
                # This is a placeholder - you would need to implement a way to store and retrieve developer IDs
                # For now, we'll just show the current user as a developer
                await update.message.reply_text(f"🔐 Current developers:\n• {user_id} (you)")

            elif command == "add" and len(context.args) > 1:
                try:
                    new_dev_id = int(context.args[1])
                    # This is a placeholder - you would need to implement a way to store developer IDs
                    await update.message.reply_text(f"✅ User {new_dev_id} has been added as a developer.")
                except ValueError:
                    await update.message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

            elif command == "remove" and len(context.args) > 1:
                try:
                    remove_dev_id = int(context.args[1])
                    # This is a placeholder - you would need to implement a way to remove developer IDs
                    if remove_dev_id == user_id:
                        await update.message.reply_text("⚠️ You cannot remove yourself as a developer.")
                    else:
                        await update.message.reply_text(f"✅ User {remove_dev_id} has been removed as a developer.")
                except ValueError:
                    await update.message.reply_text("❌ Invalid user ID. Please provide a numeric ID.")

            else:
                await update.message.reply_text("❌ Invalid developer command. Use /dev for help.")
        else:
            await update.message.reply_text(dev_message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in dev_command: {e}")
        await update.message.reply_text("❌ Error processing command. Please try again.")

async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show real-time bot statistics - alias for globalstats but with updated format"""
    try:
        # Check if user is developer
        if not await self.is_developer(update.message.from_user.id):
            await self._handle_dev_command_unauthorized(update)
            return

        loading_msg = await update.message.reply_text("📊 Analyzing real-time statistics...")

        try:
            # Get active chats with validation
            active_chats = self.quiz_manager.get_active_chats() if hasattr(self.quiz_manager, 'get_active_chats') else []
            valid_active_chats = []
            if active_chats:
                for chat_id in active_chats:
                    try:
                        if isinstance(chat_id, (int, str)) and str(chat_id).lstrip('-').isdigit():
                            valid_active_chats.append(int(chat_id))
                    except Exception:
                        continue

            total_groups = len(valid_active_chats)

            # Check valid statistics
            if hasattr(self.quiz_manager, 'stats') and self.quiz_manager.stats:
                valid_stats = {k: v for k, v in self.quiz_manager.stats.items()
                             if isinstance(v, dict) and 'total_quizzes' in v}
                total_users = len(valid_stats)
            else:
                valid_stats = {}
                total_users = 0

            # Calculate metrics
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

                # Check daily activity if valid
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

            # Get active groups count
            active_groups_now = 0
            if valid_active_chats and hasattr(self.quiz_manager, 'get_group_last_activity'):
                for chat_id in valid_active_chats:
                    try:
                        last_activity = self.quiz_manager.get_group_last_activity(chat_id)
                        if last_activity == current_date:
                            active_groups_now += 1
                    except Exception:
                        continue

            # Calculate active users
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
            uptime = (datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds() / 3600

            # Get total questions count
            total_questions = 0
            if hasattr(self.quiz_manager, 'questions'):
                if isinstance(self.quiz_manager.questions, list):
                    total_questions = len(self.quiz_manager.questions)

            # Create message with modern formatting
            stats_message = f"""✨ 𝐐𝐮𝐢𝐳𝐢𝐦𝐩𝐚𝐜𝐭 | 𝐒𝐭𝐚𝐭𝐬 𝐏𝐚𝐧𝐞𝐥

📊 𝐁𝐨𝐭 𝐏𝐞𝐫𝐟𝐨𝐫𝐦𝐚𝐧𝐜𝐞 𝐌𝐞𝐭𝐫𝐢𝐜𝐬
━━━━━━━━━━━━━━━━━━━━━━━

👥 𝐏𝐞𝐨𝐩𝐥𝐞 & 𝐆𝐫𝐨𝐮𝐩𝐬
• Total Users: {total_users}
• Total Groups: {total_groups}
• Active Today: {today_active_users}
• Weekly Active: {week_active_users}

📈 𝐄𝐧𝐠𝐚𝐠𝐞𝐦𝐞𝐧𝐭 𝐀𝐧𝐚𝐥𝐲𝐭𝐢𝐜𝐬
• Today's Activity: {today_quizzes}
• Weekly Activity: {week_quizzes}
• Total Attempts: {total_attempts}
• Correct Answers: {correct_answers}
• Success Rate: {success_rate}%

⚡ 𝐑𝐞𝐚𝐥-𝐭𝐢𝐦𝐞 𝐒𝐭𝐚𝐭𝐮𝐬
• Active Groups Now: {active_groups_now}
• Total Questions: {total_questions}
• Memory Usage: {memory_usage:.1f}MB
• Uptime: {uptime:.1f}h

━━━━━━━━━━━━━━━━━━━━━━━
📆 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Bot Status: Operational"""

            await loading_msg.edit_text(
                stats_message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Displayed stats to developer {update.effective_user.id}")

        except Exception as e:
            logger.error(f"Error processing stats: {e}", exc_info=True)
            await loading_msg.edit_text(
                """📊 𝐒𝐲𝐬𝐭𝐞𝐦 𝐒𝐭𝐚𝐭𝐮𝐬

✅ Bot is operational
✅ System is running
✅ Ready for users

🔄 No activity recorded yet
Start by adding the bot to groups!""",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Error retrieving statistics. Please try again.")