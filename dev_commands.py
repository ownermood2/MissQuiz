"""
Developer Commands Module for Telegram Quiz Bot
Handles all developer-only commands with enhanced features
"""

import logging
import asyncio
import sys
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import config
from database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DeveloperCommands:
    """Handles all developer commands with access control"""
    
    def __init__(self, db_manager: DatabaseManager, quiz_manager):
        self.db = db_manager
        self.quiz_manager = quiz_manager
        logger.info("Developer commands module initialized")
    
    async def check_access(self, update: Update) -> bool:
        """Check if user is authorized (OWNER or WIFU)"""
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return False
        
        is_authorized = user_id in config.AUTHORIZED_USERS
        
        if not is_authorized:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
        
        return is_authorized
    
    async def send_unauthorized_message(self, update: Update):
        """Send friendly unauthorized message"""
        message = await update.effective_message.reply_text(config.UNAUTHORIZED_MESSAGE)
        
        await self.auto_clean_message(update.effective_message, message)
    
    async def auto_clean_message(self, command_message, bot_reply, delay: int = 5):
        """Auto-clean command and reply messages after delay"""
        try:
            await asyncio.sleep(delay)
            try:
                await command_message.delete()
            except Exception as e:
                logger.debug(f"Could not delete command message: {e}")
            
            try:
                if bot_reply:
                    await bot_reply.delete()
            except Exception as e:
                logger.debug(f"Could not delete reply message: {e}")
        except Exception as e:
            logger.error(f"Error in auto_clean: {e}")
    
    def format_number(self, num):
        """Format numbers with K/M suffixes for readability"""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        else:
            return f"{num:,}"
    
    async def delquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete quiz questions - Fixed version without Markdown parsing errors"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            questions = self.db.get_all_questions()
            if not questions:
                reply = await update.message.reply_text(
                    "❌ No Quizzes Available\n\n"
                    "Add new quizzes using /addquiz command"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            # Handle reply to quiz case
            if update.message.reply_to_message and update.message.reply_to_message.poll:
                poll_id = update.message.reply_to_message.poll.id
                poll_data = context.bot_data.get(f"poll_{poll_id}")
                
                if not poll_data:
                    reply = await update.message.reply_text("❌ Quiz not found or expired")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                # Find the quiz
                found_idx = -1
                for idx, q in enumerate(questions):
                    if q['question'] == poll_data['question']:
                        found_idx = idx
                        break
                
                if found_idx == -1:
                    reply = await update.message.reply_text("❌ Quiz not found")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                # Show confirmation
                quiz = questions[found_idx]
                
                # Store quiz ID in user context
                context.user_data['pending_delete_quiz'] = quiz['id']
                
                confirm_text = f"🗑 Confirm Quiz Deletion\n\n"
                confirm_text += f"📌 Quiz #{quiz['id']}\n"
                confirm_text += f"❓ {quiz['question']}\n\n"
                for i, opt in enumerate(quiz['options'], 1):
                    marker = "✅" if i-1 == quiz['correct_answer'] else "⭕"
                    confirm_text += f"{i}️⃣ {opt} {marker}\n"
                confirm_text += f"\n⚠ Confirm: /delquiz_confirm\n"
                confirm_text += "❌ Cancel: Ignore this message\n\n"
                confirm_text += "💡 Once confirmed, the quiz will be permanently deleted."
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Quiz deletion confirmation shown for quiz #{quiz['id']}")
                return
            
            # Handle direct command
            if not context.args:
                reply = await update.message.reply_text(
                    "❌ Invalid Usage\n\n"
                    "Either:\n"
                    "1. Reply to a quiz with /delquiz\n"
                    "2. Use: /delquiz [quiz_number]\n\n"
                    "Use /editquiz to view available quizzes"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            try:
                quiz_id = int(context.args[0])
                quiz = next((q for q in questions if q['id'] == quiz_id), None)
                
                if not quiz:
                    reply = await update.message.reply_text(
                        f"❌ Invalid Quiz ID: {quiz_id}\n\n"
                        "Use /editquiz to view available quizzes"
                    )
                    await self.auto_clean_message(update.message, reply)
                    return
                
                # Show confirmation and store quiz ID
                context.user_data['pending_delete_quiz'] = quiz['id']
                
                confirm_text = f"🗑 Confirm Quiz Deletion\n\n"
                confirm_text += f"📌 Quiz #{quiz['id']}\n"
                confirm_text += f"❓ {quiz['question']}\n\n"
                for i, opt in enumerate(quiz['options'], 1):
                    marker = "✅" if i-1 == quiz['correct_answer'] else "⭕"
                    confirm_text += f"{i}️⃣ {opt} {marker}\n"
                confirm_text += f"\n⚠ Confirm: /delquiz_confirm\n"
                confirm_text += "❌ Cancel: Ignore this message\n\n"
                confirm_text += "💡 Once confirmed, the quiz will be permanently deleted."
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Quiz deletion confirmation shown for quiz #{quiz['id']}")
                
            except ValueError:
                reply = await update.message.reply_text(
                    "❌ Invalid Input\n\n"
                    "Please provide a valid quiz ID number\n"
                    "Usage: /delquiz [quiz_id]"
                )
                await self.auto_clean_message(update.message, reply)
        
        except Exception as e:
            logger.error(f"Error in delquiz: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error processing delete request")
            await self.auto_clean_message(update.message, reply)
    
    async def delquiz_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute quiz deletion"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Get quiz ID from context
            quiz_id = context.user_data.get('pending_delete_quiz')
            
            if not quiz_id:
                reply = await update.message.reply_text(
                    "❌ No quiz pending deletion\n\n"
                    "Please use /delquiz first to select a quiz"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            # Delete from database
            if self.db.delete_question(quiz_id):
                # Clear the pending delete
                context.user_data.pop('pending_delete_quiz', None)
                
                reply = await update.message.reply_text(
                    f"✅ Quiz #{quiz_id} deleted successfully! 🗑️\n\n"
                    f"Remaining quizzes: {len(self.db.get_all_questions())}"
                )
                logger.info(f"Quiz #{quiz_id} deleted by user {update.effective_user.id}")
                await self.auto_clean_message(update.message, reply, delay=3)
            else:
                reply = await update.message.reply_text(f"❌ Quiz #{quiz_id} not found")
                await self.auto_clean_message(update.message, reply)
        
        except Exception as e:
            logger.error(f"Error in delquiz_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error deleting quiz")
            await self.auto_clean_message(update.message, reply)
    
    async def dev(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced developer management command"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            if not context.args:
                reply = await update.message.reply_text(
                    "🔧 Developer Management\n\n"
                    "Commands:\n"
                    "• /dev add [user_id] - Add developer\n"
                    "• /dev remove [user_id] - Remove developer\n"
                    "• /dev list - Show all developers"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            action = context.args[0].lower()
            
            if action == "add":
                if len(context.args) < 2:
                    reply = await update.message.reply_text("❌ Usage: /dev add [user_id]")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                try:
                    new_dev_id = int(context.args[1])
                    self.db.add_developer(new_dev_id, added_by=update.effective_user.id)
                    reply = await update.message.reply_text(
                        f"✅ Developer added successfully!\n\n"
                        f"User ID: {new_dev_id}"
                    )
                    logger.info(f"Developer {new_dev_id} added by {update.effective_user.id}")
                    await self.auto_clean_message(update.message, reply)
                
                except ValueError:
                    reply = await update.message.reply_text("❌ Invalid user ID")
                    await self.auto_clean_message(update.message, reply)
            
            elif action == "remove":
                if len(context.args) < 2:
                    reply = await update.message.reply_text("❌ Usage: /dev remove [user_id]")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                try:
                    dev_id = int(context.args[1])
                    
                    if dev_id in config.AUTHORIZED_USERS:
                        reply = await update.message.reply_text("❌ Cannot remove OWNER or WIFU")
                        await self.auto_clean_message(update.message, reply)
                        return
                    
                    if self.db.remove_developer(dev_id):
                        reply = await update.message.reply_text(f"✅ Developer {dev_id} removed")
                        logger.info(f"Developer {dev_id} removed by {update.effective_user.id}")
                        await self.auto_clean_message(update.message, reply)
                    else:
                        reply = await update.message.reply_text(f"❌ Developer {dev_id} not found")
                        await self.auto_clean_message(update.message, reply)
                
                except ValueError:
                    reply = await update.message.reply_text("❌ Invalid user ID")
                    await self.auto_clean_message(update.message, reply)
            
            elif action == "list":
                developers = self.db.get_all_developers()
                
                if not developers:
                    reply = await update.message.reply_text("📋 No additional developers configured")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                dev_text = "👥 Developer List\n\n"
                for dev in developers:
                    name = dev.get('first_name') or dev.get('username') or f"User {dev['user_id']}"
                    dev_text += f"• {name} (ID: {dev['user_id']})\n"
                
                reply = await update.message.reply_text(dev_text)
                await self.auto_clean_message(update.message, reply)
            
            else:
                reply = await update.message.reply_text("❌ Unknown action. Use: add, remove, or list")
                await self.auto_clean_message(update.message, reply)
        
        except Exception as e:
            logger.error(f"Error in dev command: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error executing command")
            await self.auto_clean_message(update.message, reply)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced statistics command with today, week, month, and all-time data"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            loading = await update.message.reply_text("📊 Loading statistics...")
            
            try:
                stats = self.db.get_stats_summary()
                
                # Format numbers with K/M suffixes
                groups_fmt = self.format_number(stats['total_groups'])
                users_fmt = self.format_number(stats['total_users'])
                today_fmt = self.format_number(stats['quizzes_today'])
                week_fmt = self.format_number(stats['quizzes_week'])
                month_fmt = self.format_number(stats['quizzes_month'])
                alltime_fmt = self.format_number(stats['quizzes_alltime'])
                
                stats_text = "🚀 Bot Stats Dashboard\n"
                stats_text += f"✨ Groups: {groups_fmt} 🌐\n"
                stats_text += f"🔥 Users: {users_fmt} 🚀\n\n"
                
                stats_text += "📊 Quizzes Fired Up!\n"
                stats_text += f"⚡ Today: {today_fmt}\n"
                stats_text += f"📆 This Week: {week_fmt}\n"
                stats_text += f"📈 This Month: {month_fmt}\n"
                stats_text += f"🏆 All Time: {alltime_fmt}\n\n"
                
                stats_text += "💡 Knowledge never sleeps. Neither do we. 😎"
                
                # Create interactive buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
                        InlineKeyboardButton("👥 Top Users", callback_data="stats_top_users")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await loading.edit_text(stats_text, reply_markup=reply_markup)
                logger.info(f"Stats displayed to {update.effective_user.id}")
            
            except Exception as e:
                logger.error(f"Error generating stats: {e}", exc_info=True)
                await loading.edit_text("❌ Error generating statistics")
        
        except Exception as e:
            logger.error(f"Error in stats command: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error retrieving statistics")
            await self.auto_clean_message(update.message, reply)
    
    async def allreload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart bot globally without downtime"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            await update.message.reply_text(
                "🔄 Restarting bot now...\n\n"
                "⏳ The bot will be back in a few seconds."
            )
            
            logger.info(f"Bot restart initiated by user {update.effective_user.id}")
            
            # Give time for message to send
            await asyncio.sleep(0.5)
            
            # Restart the process properly
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        except Exception as e:
            logger.error(f"Error in allreload: {e}", exc_info=True)
            await update.message.reply_text("❌ Error restarting bot")
    
    async def broadband(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send simple broadcast message without forward tags"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            if not context.args:
                reply = await update.message.reply_text(
                    "📢 Broadcast Message\n\n"
                    "Usage: /broadband [message text]\n\n"
                    "This will send a plain text message to all users and groups."
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            message_text = ' '.join(context.args)
            
            # Get all users and groups
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            
            total_targets = len(users) + len(groups)
            
            confirm_text = f"📢 Broadcast Confirmation\n\n"
            confirm_text += f"Message: {message_text}\n\n"
            confirm_text += f"Will be sent to:\n"
            confirm_text += f"• {len(users)} users\n"
            confirm_text += f"• {len(groups)} groups\n"
            confirm_text += f"• Total: {total_targets} recipients\n\n"
            confirm_text += f"Confirm: /broadband_confirm"
            
            # Store broadcast data temporarily
            context.user_data['broadcast_message'] = message_text
            context.user_data['broadcast_type'] = 'plain'
            
            reply = await update.message.reply_text(confirm_text)
            logger.info(f"Broadcast prepared by {update.effective_user.id}")
        
        except Exception as e:
            logger.error(f"Error in broadband: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadband_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and send broadband broadcast"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            message_text = context.user_data.get('broadcast_message')
            if not message_text:
                reply = await update.message.reply_text("❌ No broadcast message found. Please use /broadband first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("📢 Sending broadcast...")
            
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            
            success_count = 0
            fail_count = 0
            
            # Send to users
            for user in users:
                try:
                    await context.bot.send_message(chat_id=user['user_id'], text=message_text)
                    success_count += 1
                    await asyncio.sleep(0.05)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Failed to send to user {user['user_id']}: {e}")
                    fail_count += 1
            
            # Send to groups
            for group in groups:
                try:
                    await context.bot.send_message(chat_id=group['chat_id'], text=message_text)
                    success_count += 1
                    await asyncio.sleep(0.05)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Failed to send to group {group['chat_id']}: {e}")
                    fail_count += 1
            
            await status.edit_text(
                f"✅ Broadcast completed!\n\n"
                f"• Sent: {success_count}\n"
                f"• Failed: {fail_count}"
            )
            
            logger.info(f"Broadcast completed by {update.effective_user.id}: {success_count} sent, {fail_count} failed")
            
            # Clear broadcast data
            context.user_data.pop('broadcast_message', None)
            context.user_data.pop('broadcast_type', None)
        
        except Exception as e:
            logger.error(f"Error in broadband_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error sending broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced broadcast supporting both reply and direct message"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Check if replying to a message
            if update.message.reply_to_message:
                replied_message = update.message.reply_to_message
                
                users = self.db.get_all_users_stats()
                groups = self.db.get_all_groups()
                total_targets = len(users) + len(groups)
                
                confirm_text = f"📢 Broadcast Confirmation\n\n"
                confirm_text += f"Forwarding message to:\n"
                confirm_text += f"• {len(users)} users\n"
                confirm_text += f"• {len(groups)} groups\n"
                confirm_text += f"• Total: {total_targets} recipients\n\n"
                confirm_text += f"Confirm: /broadcast_confirm"
                
                # Store message ID for forwarding
                context.user_data['broadcast_message_id'] = replied_message.message_id
                context.user_data['broadcast_chat_id'] = replied_message.chat_id
                context.user_data['broadcast_type'] = 'forward'
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Broadcast (forward) prepared by {update.effective_user.id}")
            
            elif context.args:
                message_text = ' '.join(context.args)
                
                users = self.db.get_all_users_stats()
                groups = self.db.get_all_groups()
                total_targets = len(users) + len(groups)
                
                confirm_text = f"📢 Broadcast Confirmation\n\n"
                confirm_text += f"Message: {message_text}\n\n"
                confirm_text += f"Will be sent to:\n"
                confirm_text += f"• {len(users)} users\n"
                confirm_text += f"• {len(groups)} groups\n"
                confirm_text += f"• Total: {total_targets} recipients\n\n"
                confirm_text += f"Confirm: /broadcast_confirm"
                
                context.user_data['broadcast_message'] = message_text
                context.user_data['broadcast_type'] = 'text'
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Broadcast (text) prepared by {update.effective_user.id}")
            
            else:
                reply = await update.message.reply_text(
                    "📢 Broadcast Message\n\n"
                    "Usage:\n"
                    "1. Reply to a message with /broadcast (will forward that message)\n"
                    "2. /broadcast [message text] (will send as new message)\n\n"
                    "The message will be sent to all users and groups."
                )
                await self.auto_clean_message(update.message, reply)
        
        except Exception as e:
            logger.error(f"Error in broadcast: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadcast_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and send broadcast"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            broadcast_type = context.user_data.get('broadcast_type')
            if not broadcast_type:
                reply = await update.message.reply_text("❌ No broadcast found. Please use /broadcast first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("📢 Sending broadcast...")
            
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            
            success_count = 0
            fail_count = 0
            
            if broadcast_type == 'forward':
                message_id = context.user_data.get('broadcast_message_id')
                chat_id = context.user_data.get('broadcast_chat_id')
                
                # Forward to users
                for user in users:
                    try:
                        await context.bot.copy_message(
                            chat_id=user['user_id'],
                            from_chat_id=chat_id,
                            message_id=message_id
                        )
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.debug(f"Failed to send to user {user['user_id']}: {e}")
                        fail_count += 1
                
                # Forward to groups
                for group in groups:
                    try:
                        await context.bot.copy_message(
                            chat_id=group['chat_id'],
                            from_chat_id=chat_id,
                            message_id=message_id
                        )
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.debug(f"Failed to send to group {group['chat_id']}: {e}")
                        fail_count += 1
            
            else:  # text broadcast
                message_text = context.user_data.get('broadcast_message')
                
                # Send to users
                for user in users:
                    try:
                        await context.bot.send_message(chat_id=user['user_id'], text=message_text)
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.debug(f"Failed to send to user {user['user_id']}: {e}")
                        fail_count += 1
                
                # Send to groups
                for group in groups:
                    try:
                        await context.bot.send_message(chat_id=group['chat_id'], text=message_text)
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.debug(f"Failed to send to group {group['chat_id']}: {e}")
                        fail_count += 1
            
            await status.edit_text(
                f"✅ Broadcast completed!\n\n"
                f"• Sent: {success_count}\n"
                f"• Failed: {fail_count}"
            )
            
            logger.info(f"Broadcast completed by {update.effective_user.id}: {success_count} sent, {fail_count} failed")
            
            # Clear broadcast data
            context.user_data.pop('broadcast_message', None)
            context.user_data.pop('broadcast_message_id', None)
            context.user_data.pop('broadcast_chat_id', None)
            context.user_data.pop('broadcast_type', None)
        
        except Exception as e:
            logger.error(f"Error in broadcast_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error sending broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def delbroadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a broadcast message from all groups/users"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Check if replying to a broadcast message
            if not update.message.reply_to_message:
                reply = await update.message.reply_text(
                    "❌ Reply to a broadcast message with /delbroadcast to delete it from all chats"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            replied_message = update.message.reply_to_message
            
            # Confirm deletion
            confirm_text = (
                "🗑️ Delete Broadcast Confirmation\n\n"
                "This will attempt to delete the replied message from all users and groups.\n\n"
                "⚠️ Note: Messages can only be deleted if:\n"
                "• Bot is admin in groups\n"
                "• Message is less than 48 hours old\n\n"
                "Confirm: /delbroadcast_confirm"
            )
            
            # Store message info
            context.user_data['delbroadcast_message_id'] = replied_message.message_id
            context.user_data['delbroadcast_chat_id'] = replied_message.chat_id
            
            reply = await update.message.reply_text(confirm_text)
            logger.info(f"Broadcast deletion prepared by {update.effective_user.id}")
        
        except Exception as e:
            logger.error(f"Error in delbroadcast: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast deletion")
            await self.auto_clean_message(update.message, reply)
    
    async def delbroadcast_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute broadcast deletion"""
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            message_id = context.user_data.get('delbroadcast_message_id')
            if not message_id:
                reply = await update.message.reply_text("❌ No broadcast deletion found. Please use /delbroadcast first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("🗑️ Deleting broadcast messages...")
            
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            
            success_count = 0
            fail_count = 0
            
            # Delete from users
            for user in users:
                try:
                    await context.bot.delete_message(chat_id=user['user_id'], message_id=message_id)
                    success_count += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Failed to delete from user {user['user_id']}: {e}")
                    fail_count += 1
            
            # Delete from groups
            for group in groups:
                try:
                    await context.bot.delete_message(chat_id=group['chat_id'], message_id=message_id)
                    success_count += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.debug(f"Failed to delete from group {group['chat_id']}: {e}")
                    fail_count += 1
            
            await status.edit_text(
                f"✅ Broadcast deletion completed!\n\n"
                f"• Deleted: {success_count}\n"
                f"• Failed: {fail_count}\n\n"
                f"Note: Failures are normal for messages older than 48h or where bot lacks permissions."
            )
            
            logger.info(f"Broadcast deletion by {update.effective_user.id}: {success_count} deleted, {fail_count} failed")
            
            # Clear data
            context.user_data.pop('delbroadcast_message_id', None)
            context.user_data.pop('delbroadcast_chat_id', None)
        
        except Exception as e:
            logger.error(f"Error in delbroadcast_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error deleting broadcast")
            await self.auto_clean_message(update.message, reply)
