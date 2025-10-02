"""
Developer Commands Module for Telegram Quiz Bot
Handles all developer-only commands with enhanced features
"""

import logging
import asyncio
import sys
import os
import re
import json
import time
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
        """Check if user is authorized (OWNER, WIFU, or any developer in database)"""
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return False
        
        # Check if user is OWNER or WIFU
        if user_id in config.AUTHORIZED_USERS:
            return True
        
        # Check if user is in developers database
        developers = self.db.get_all_developers()
        is_developer = any(dev['user_id'] == user_id for dev in developers)
        
        if not is_developer:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
        
        return is_developer
    
    async def send_unauthorized_message(self, update: Update):
        """Send friendly unauthorized message"""
        message = await update.effective_message.reply_text(config.UNAUTHORIZED_MESSAGE)
        
        await self.auto_clean_message(update.effective_message, message)
    
    async def auto_clean_message(self, command_message, bot_reply, delay: int = 5):
        """Auto-clean command and reply messages after delay (ONLY in groups, not in PM)"""
        try:
            # Only auto-clean in groups, not in private chats
            chat_type = command_message.chat.type if command_message else None
            if chat_type not in ["group", "supergroup"]:
                logger.debug(f"Skipping auto-clean for {chat_type} chat (PM mode)")
                return
            
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
    
    def format_relative_time(self, timestamp_str):
        """Convert ISO timestamp to relative time (e.g., '5m ago', '2h ago')"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now()
            
            if dt.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            
            diff = now - dt
            seconds = int(diff.total_seconds())
            
            if seconds < 60:
                return f"{seconds}s ago"
            elif seconds < 3600:
                return f"{seconds // 60}m ago"
            elif seconds < 86400:
                return f"{seconds // 3600}h ago"
            else:
                return f"{diff.days}d ago"
        except Exception as e:
            logger.error(f"Error formatting relative time: {e}")
            return "recently"
    
    def parse_inline_buttons(self, text: str) -> tuple:
        """
        Parse inline buttons from text format with robust support for multiple formats:
        - Single row: [["Button1","URL1"],["Button2","URL2"]] → 2 buttons in 1 row
        - Multiple rows: [[["B1","URL1"],["B2","URL2"]],[["B3","URL3"]]] → 2 rows
        Returns: (cleaned_text, InlineKeyboardMarkup or None)
        """
        try:
            # Trim whitespace and newlines from text
            text = text.strip()
            
            # More forgiving regex: match [[...]] at end, allow trailing whitespace/newlines
            button_pattern = r'\[\[(.*?)\]\]\s*$'
            match = re.search(button_pattern, text, re.DOTALL)
            
            if not match:
                return text, None
            
            # Extract button JSON and clean text
            button_json = '[[' + match.group(1) + ']]'
            cleaned_text = text[:match.start()].strip()
            
            # Parse button data
            button_data = json.loads(button_json)
            
            if not button_data or not isinstance(button_data, list):
                return text, None
            
            # Determine format: nested array (multiple rows) or flat array (single row)
            keyboard = []
            total_buttons = 0
            
            # Check if it's a nested array (multiple rows format)
            if button_data and isinstance(button_data[0], list) and len(button_data[0]) > 0 and isinstance(button_data[0][0], list):
                # Multiple rows format: [[["B1","URL1"],["B2","URL2"]],[["B3","URL3"]]]
                for row_data in button_data:
                    if not isinstance(row_data, list):
                        continue
                    
                    row_buttons = []
                    for button in row_data:
                        if total_buttons >= 100:  # Telegram limit: 100 buttons total
                            break
                        
                        if isinstance(button, list) and len(button) >= 2:
                            button_text = str(button[0]).strip()
                            button_url = str(button[1]).strip()
                            
                            # Validate URL scheme
                            if button_text and button_url and (
                                button_url.startswith('http://') or 
                                button_url.startswith('https://') or 
                                button_url.startswith('t.me/')
                            ):
                                row_buttons.append(InlineKeyboardButton(button_text, url=button_url))
                                total_buttons += 1
                                
                                if len(row_buttons) >= 8:  # Telegram limit: 8 buttons per row
                                    break
                    
                    if row_buttons:
                        keyboard.append(row_buttons)
                    
                    if total_buttons >= 100:
                        break
            
            else:
                # Single row format: [["Button1","URL1"],["Button2","URL2"]]
                row_buttons = []
                for button in button_data:
                    if total_buttons >= 100:
                        break
                    
                    if isinstance(button, list) and len(button) >= 2:
                        button_text = str(button[0]).strip()
                        button_url = str(button[1]).strip()
                        
                        # Validate URL scheme
                        if button_text and button_url and (
                            button_url.startswith('http://') or 
                            button_url.startswith('https://') or 
                            button_url.startswith('t.me/')
                        ):
                            row_buttons.append(InlineKeyboardButton(button_text, url=button_url))
                            total_buttons += 1
                            
                            if len(row_buttons) >= 8:
                                break
                
                if row_buttons:
                    keyboard.append(row_buttons)
            
            if keyboard:
                logger.info(f"Parsed {sum(len(row) for row in keyboard)} inline buttons in {len(keyboard)} row(s) from broadcast text")
                return cleaned_text, InlineKeyboardMarkup(keyboard)
            
            return text, None
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse button JSON: {e}")
            return text, None
        except Exception as e:
            logger.error(f"Error parsing inline buttons: {e}")
            return text, None
    
    async def replace_placeholders(self, text: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, 
                                   user_data: dict = None, group_data: dict = None, 
                                   bot_name_cache: str = None) -> str:
        """
        Replace placeholders in text (OPTIMIZED - uses database data to avoid API calls):
        {first_name} -> recipient's first name
        {username} -> recipient's username (with @)
        {chat_title} -> group title or first name for PMs
        {bot_name} -> bot's name
        
        Args:
            text: Text with placeholders
            chat_id: Chat ID for fallback lookup
            context: Telegram context
            user_data: User dict from database (if PM) - has first_name, username
            group_data: Group dict from database (if group) - has chat_title
            bot_name_cache: Cached bot name to avoid repeated lookups
        """
        if not text:
            return text
        
        try:
            # Replace bot name (use cached value to avoid API call)
            bot_name = bot_name_cache if bot_name_cache else (context.bot.first_name or "Bot")
            text = text.replace('{bot_name}', bot_name)
            
            # Use provided data from database instead of making API call
            if user_data:
                # PM - use user's info from database
                first_name = user_data.get('first_name') or "User"
                username = f"@{user_data.get('username')}" if user_data.get('username') else "User"
                chat_title = first_name
            elif group_data:
                # Group - use group info from database
                first_name = "Member"
                username = "User"
                chat_title = group_data.get('chat_title') or "Group"
            else:
                # Fallback: fetch from API only if data not provided
                try:
                    chat = await context.bot.get_chat(chat_id)
                    if chat.type == 'private':
                        first_name = chat.first_name or "User"
                        username = f"@{chat.username}" if chat.username else "User"
                        chat_title = first_name
                    else:
                        first_name = "Member"
                        username = "User"
                        chat_title = chat.title or "Group"
                except Exception as api_error:
                    logger.warning(f"Fallback get_chat failed for {chat_id}: {api_error}")
                    first_name = "User"
                    username = "User"
                    chat_title = "Chat"
            
            text = text.replace('{first_name}', first_name)
            text = text.replace('{username}', username)
            text = text.replace('{chat_title}', chat_title)
            
            return text
        
        except Exception as e:
            logger.error(f"Error replacing placeholders for chat {chat_id}: {e}")
            return text
    
    async def delquiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete quiz questions - Fixed version without Markdown parsing errors"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Log command execution immediately
            quiz_id_arg = context.args[0] if context.args else None
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/delquiz',
                details={'quiz_id': quiz_id_arg, 'reply_mode': bool(update.message.reply_to_message)},
                success=True
            )
            
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
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /delquiz completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/delquiz',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in delquiz: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error processing delete request")
            await self.auto_clean_message(update.message, reply)
    
    async def delquiz_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute quiz deletion"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Get quiz ID from context
            quiz_id = context.user_data.get('pending_delete_quiz')
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/delquiz_confirm',
                details={'quiz_id': quiz_id, 'action': 'confirm_deletion'},
                success=True
            )
            
            if not quiz_id:
                reply = await update.message.reply_text(
                    "❌ No quiz pending deletion\n\n"
                    "Please use /delquiz first to select a quiz"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            # Get quiz details before deletion for logging
            questions = self.db.get_all_questions()
            quiz_to_delete = next((q for q in questions if q['id'] == quiz_id), None)
            
            # Delete from database
            if self.db.delete_question(quiz_id):
                # CRITICAL FIX: Also delete from quiz_manager's in-memory list and JSON file
                # Match by question text since JSON questions don't have IDs
                if quiz_to_delete:
                    try:
                        json_questions = self.quiz_manager.get_all_questions()
                        # Find matching question by text
                        quiz_index = next(
                            (i for i, q in enumerate(json_questions) 
                             if q.get('question', '').strip() == quiz_to_delete['question'].strip()),
                            None
                        )
                        
                        if quiz_index is not None:
                            self.quiz_manager.delete_question(quiz_index)
                            logger.info(f"Deleted quiz from quiz_manager at index {quiz_index}")
                        else:
                            logger.warning(f"Could not find quiz in quiz_manager with question: {quiz_to_delete['question'][:50]}")
                    except Exception as e:
                        logger.error(f"Error deleting from quiz_manager: {e}")
                
                # Clear the pending delete
                context.user_data.pop('pending_delete_quiz', None)
                
                # Log comprehensive quiz deletion activity
                self.db.log_activity(
                    activity_type='quiz_deleted',
                    user_id=update.effective_user.id,
                    chat_id=update.effective_chat.id,
                    username=update.effective_user.username,
                    chat_title=getattr(update.effective_chat, 'title', None),
                    details={
                        'deleted_quiz_id': quiz_id,
                        'question_text': quiz_to_delete['question'][:100] if quiz_to_delete else None,
                        'remaining_quizzes': len(self.db.get_all_questions())
                    },
                    success=True
                )
                
                reply = await update.message.reply_text(
                    f"✅ Quiz #{quiz_id} deleted successfully! 🗑️\n\n"
                    f"Remaining quizzes: {len(self.quiz_manager.get_all_questions())}"
                )
                logger.info(f"Quiz #{quiz_id} deleted by user {update.effective_user.id}")
                await self.auto_clean_message(update.message, reply, delay=3)
            else:
                reply = await update.message.reply_text(f"❌ Quiz #{quiz_id} not found")
                await self.auto_clean_message(update.message, reply)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /delquiz_confirm completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/delquiz_confirm',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in delquiz_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error deleting quiz")
            await self.auto_clean_message(update.message, reply)
    
    async def dev(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced developer management command"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Determine action for logging
            action = 'help' if not context.args else (context.args[0] if not context.args[0].isdigit() else 'quick_add')
            target_user = context.args[1] if len(context.args) > 1 else (context.args[0] if context.args and context.args[0].isdigit() else None)
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/dev',
                details={'action': action, 'target_user': target_user},
                success=True
            )
            
            if not context.args:
                reply = await update.message.reply_text(
                    "🔧 Developer Management\n\n"
                    "Commands:\n"
                    "• /dev [user_id] - Add developer (quick add)\n"
                    "• /dev add [user_id] - Add developer\n"
                    "• /dev remove [user_id] - Remove developer\n"
                    "• /dev list - Show all developers"
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            # Check if first argument is a number (user ID for quick add)
            try:
                user_id = int(context.args[0])
                # Quick add: /dev 123456
                # Try to fetch user info from Telegram
                try:
                    user_info = await context.bot.get_chat(user_id)
                    username = user_info.username if hasattr(user_info, 'username') else None
                    first_name = user_info.first_name if hasattr(user_info, 'first_name') else None
                    last_name = user_info.last_name if hasattr(user_info, 'last_name') else None
                    
                    self.db.add_developer(
                        user_id=user_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        added_by=update.effective_user.id
                    )
                    
                    display_name = first_name or username or f"User {user_id}"
                    reply = await update.message.reply_text(
                        f"✅ Developer added successfully!\n\n"
                        f"👤 {display_name}\n"
                        f"🆔 ID: {user_id}"
                    )
                except Exception as e:
                    logger.warning(f"Could not fetch user info for {user_id}: {e}")
                    # Add without user info
                    self.db.add_developer(user_id, added_by=update.effective_user.id)
                    reply = await update.message.reply_text(
                        f"✅ Developer added successfully!\n\n"
                        f"User ID: {user_id}\n"
                        f"⚠️ Could not fetch user details"
                    )
                
                logger.info(f"Developer {user_id} added by {update.effective_user.id}")
                await self.auto_clean_message(update.message, reply)
                return
            except ValueError:
                # Not a number, treat as action
                pass
            
            action = context.args[0].lower()
            
            if action == "add":
                if len(context.args) < 2:
                    reply = await update.message.reply_text("❌ Usage: /dev add [user_id]")
                    await self.auto_clean_message(update.message, reply)
                    return
                
                try:
                    new_dev_id = int(context.args[1])
                    
                    # Try to fetch user info from Telegram
                    try:
                        user_info = await context.bot.get_chat(new_dev_id)
                        username = user_info.username if hasattr(user_info, 'username') else None
                        first_name = user_info.first_name if hasattr(user_info, 'first_name') else None
                        last_name = user_info.last_name if hasattr(user_info, 'last_name') else None
                        
                        self.db.add_developer(
                            user_id=new_dev_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            added_by=update.effective_user.id
                        )
                        
                        display_name = first_name or username or f"User {new_dev_id}"
                        reply = await update.message.reply_text(
                            f"✅ Developer added successfully!\n\n"
                            f"👤 {display_name}\n"
                            f"🆔 ID: {new_dev_id}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not fetch user info for {new_dev_id}: {e}")
                        # Add without user info
                        self.db.add_developer(new_dev_id, added_by=update.effective_user.id)
                        reply = await update.message.reply_text(
                            f"✅ Developer added successfully!\n\n"
                            f"User ID: {new_dev_id}\n"
                            f"⚠️ Could not fetch user details"
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
                
                dev_text = "👥 Developer List\n\n"
                
                # Get OWNER and WIFU info with clickable profile links
                owner_info = []
                wifu_info = []
                
                try:
                    # Fetch OWNER info
                    owner_user = await context.bot.get_chat(config.OWNER_ID)
                    owner_name = f"[{owner_user.first_name}](tg://user?id={config.OWNER_ID})"
                    owner_info.append(f"{owner_name} (ID: {config.OWNER_ID})")
                except:
                    owner_info.append(f"@CV_OWNER (ID: {config.OWNER_ID})")
                
                # Fetch WIFU info if exists
                if config.WIFU_ID:
                    try:
                        wifu_user = await context.bot.get_chat(config.WIFU_ID)
                        wifu_name = f"[{wifu_user.first_name}](tg://user?id={config.WIFU_ID})"
                        wifu_info.append(f"{wifu_name} (ID: {config.WIFU_ID})")
                    except:
                        wifu_info.append(f"WIFU (ID: {config.WIFU_ID})")
                
                # Build owner/wifu line
                if wifu_info:
                    dev_text += f"👑 {owner_info[0]} & {wifu_info[0]} 🤌❤️\n"
                else:
                    dev_text += f"👑 {owner_info[0]} & OWNER WIFU 🤌❤️\n"
                
                dev_text += "---\n"
                dev_text += "🛡 Admin List\n\n"
                
                # Show other developers with clickable profile links
                if not developers:
                    dev_text += "No additional admins configured"
                else:
                    for dev in developers:
                        try:
                            dev_user = await context.bot.get_chat(dev['user_id'])
                            dev_name = f"[{dev_user.first_name}](tg://user?id={dev['user_id']})"
                            dev_text += f"▫️ {dev_name} (ID: {dev['user_id']})\n"
                        except:
                            # Fallback if can't fetch user info
                            username = f"@{dev.get('username')}" if dev.get('username') else dev.get('first_name') or f"User{dev['user_id']}"
                            dev_text += f"▫️ {username} (ID: {dev['user_id']})\n"
                
                reply = await update.message.reply_text(dev_text, parse_mode=ParseMode.MARKDOWN)
                await self.auto_clean_message(update.message, reply)
            
            else:
                reply = await update.message.reply_text("❌ Unknown action. Use: add, remove, or list")
                await self.auto_clean_message(update.message, reply)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /dev completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/dev',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in dev command: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error executing command")
            await self.auto_clean_message(update.message, reply)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced real-time statistics dashboard with live activity feed"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/stats',
                details={'stats_type': 'real_time_dashboard'},
                success=True
            )
            
            loading = await update.message.reply_text("📊 Loading real-time statistics...")
            
            try:
                # Get user & group metrics
                all_users = self.db.get_all_users_stats()
                total_users = len(all_users)
                
                all_groups = self.db.get_all_groups()
                total_groups = len(all_groups)
                
                user_engagement = self.db.get_user_engagement_stats()
                active_today = user_engagement.get('active_today', 0)
                
                # Get quiz activity (real-time from activity_logs)
                quiz_stats_today = self.db.get_quiz_stats_by_period('today')
                quiz_stats_week = self.db.get_quiz_stats_by_period('week')
                
                quizzes_today = quiz_stats_today.get('quizzes_sent', 0)
                answered_today = quiz_stats_today.get('quizzes_answered', 0)
                quizzes_week = quiz_stats_week.get('quizzes_sent', 0)
                success_rate = quiz_stats_week.get('success_rate', 0)
                
                # Get performance metrics (24h)
                perf_summary = self.db.get_performance_summary(24)
                avg_time = int(perf_summary.get('avg_response_time', 0))
                
                # Get total commands executed in last 24h
                activity_stats_24h = self.db.get_activity_stats(1)
                commands_24h = activity_stats_24h.get('activities_by_type', {}).get('command', 0)
                
                # Get error rate
                error_stats = self.db.get_error_rate_stats(1)
                error_rate = error_stats.get('error_rate', 0)
                
                # Get top commands (last 7 days)
                command_usage = self.db.get_command_usage_stats(7)
                top_commands = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)[:5]
                
                if top_commands:
                    command_list = "\n".join([f"• {cmd}: {count:,}x" for cmd, count in top_commands])
                else:
                    command_list = "• No commands yet"
                
                # Get recent activity feed (last 10 activities)
                recent_activities = self.db.get_recent_activities(limit=10)
                activity_feed = ""
                
                if recent_activities:
                    for activity in recent_activities:
                        time_ago = self.format_relative_time(activity.get('timestamp', ''))
                        activity_type = activity.get('activity_type', 'unknown')
                        username = activity.get('username', 'Unknown')
                        command = activity.get('command', '')
                        
                        if activity_type == 'command' and command:
                            activity_feed += f"• {time_ago}: @{username} used {command}\n"
                        elif activity_type == 'quiz_sent':
                            activity_feed += f"• {time_ago}: Quiz sent\n"
                        elif activity_type == 'quiz_answered':
                            activity_feed += f"• {time_ago}: @{username} answered quiz\n"
                        elif activity_type == 'broadcast':
                            activity_feed += f"• {time_ago}: Broadcast sent\n"
                        elif activity_type == 'error':
                            activity_feed += f"• {time_ago}: Error logged\n"
                        else:
                            activity_feed += f"• {time_ago}: {activity_type}\n"
                else:
                    activity_feed = "• No recent activity"
                
                # Format the complete stats message
                current_time = datetime.now().strftime('%H:%M:%S')
                
                stats_text = (
                    f"📊 **Live Bot Statistics**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👥 **Users & Groups**\n"
                    f"• Total Users: {total_users:,}\n"
                    f"• Total Groups: {total_groups:,}\n"
                    f"• Active Today: {active_today}\n\n"
                    f"📝 **Quiz Activity**\n"
                    f"• Today: {quizzes_today} sent, {answered_today} answered\n"
                    f"• This Week: {quizzes_week} sent\n"
                    f"• Success Rate: {success_rate}%\n\n"
                    f"⚡ **Performance (24h)**\n"
                    f"• Avg Response: {avg_time}ms\n"
                    f"• Commands: {commands_24h:,}\n"
                    f"• Error Rate: {error_rate}%\n\n"
                    f"🔥 **Top Commands (7 days)**\n"
                    f"{command_list}\n\n"
                    f"📜 **Recent Activity**\n"
                    f"{activity_feed}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🕐 Updated: {current_time}"
                )
                
                await loading.edit_text(stats_text, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Real-time stats displayed to {update.effective_user.id}")
            
            except Exception as e:
                logger.error(f"Error generating real-time stats: {e}", exc_info=True)
                await loading.edit_text("❌ Error generating statistics. Please try again.")
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /stats completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/stats',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in stats command: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error retrieving statistics")
            await self.auto_clean_message(update.message, reply)
    
    async def broadband(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send simple broadcast message without forward tags"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Get recipient counts for logging
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            total_targets = len(users) + len(groups)
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/broadband',
                details={'recipient_count': total_targets, 'users': len(users), 'groups': len(groups)},
                success=True
            )
            
            if not context.args:
                reply = await update.message.reply_text(
                    "📢 Broadcast Message\n\n"
                    "Usage: /broadband [message text]\n\n"
                    "This will send a plain text message to all users and groups."
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            message_text = ' '.join(context.args)
            
            # Get all users and groups - SEND TO ALL STORED USERS AND GROUPS
            users = self.db.get_all_users_stats()  # Get ALL users, not just active
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
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /broadband completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/broadband',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in broadband: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadband_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and send broadband broadcast"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Log command execution immediately  
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/broadband_confirm',
                details={'action': 'confirm_broadcast'},
                success=True
            )
            
            message_text = context.user_data.get('broadcast_message')
            if not message_text:
                reply = await update.message.reply_text("❌ No broadcast message found. Please use /broadband first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("📢 Sending broadcast...")
            
            # Get ALL users and groups - SEND TO ALL STORED USERS AND GROUPS
            users = self.db.get_all_users_stats()  # Get ALL users, not just active
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
                f"✅ Total Sent: {success_count}\n"
                f"❌ Failed: {fail_count}"
            )
            
            logger.info(f"Broadcast completed by {update.effective_user.id}: {success_count} sent, {fail_count} failed")
            
            # Clear broadcast data
            context.user_data.pop('broadcast_message', None)
            context.user_data.pop('broadcast_type', None)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /broadband_confirm completed in {response_time}ms - sent: {success_count}, failed: {fail_count}")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/broadband_confirm',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in broadband_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error sending broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced broadcast supporting media, buttons, placeholders, and auto-cleanup"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Determine media type and recipient counts for logging
            users = self.db.get_all_users_stats()
            groups = self.db.get_all_groups()
            total_targets = len(users) + len(groups)
            
            # Determine initial media type for logging
            if update.message.reply_to_message:
                replied_msg = update.message.reply_to_message
                if replied_msg.photo:
                    media_type = 'photo'
                elif replied_msg.video:
                    media_type = 'video'
                elif replied_msg.document:
                    media_type = 'document'
                elif replied_msg.animation:
                    media_type = 'animation'
                else:
                    media_type = 'forward'
            elif context.args:
                media_type = 'text'
            else:
                media_type = 'help'
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/broadcast',
                details={'recipient_count': total_targets, 'media_type': media_type, 'users': len(users), 'groups': len(groups)},
                success=True
            )
            
            # Check if replying to a message
            if update.message.reply_to_message:
                replied_message = update.message.reply_to_message
                
                users = self.db.get_all_users_stats()
                groups = self.db.get_all_groups()
                total_targets = len(users) + len(groups)
                
                # Detect media type
                media_type = None
                media_file_id = None
                media_caption = None
                media_preview = ""
                
                if replied_message.photo:
                    media_type = 'photo'
                    media_file_id = replied_message.photo[-1].file_id
                    media_caption = replied_message.caption
                    media_preview = "📷 Photo"
                    logger.info("Detected photo in broadcast")
                elif replied_message.video:
                    media_type = 'video'
                    media_file_id = replied_message.video.file_id
                    media_caption = replied_message.caption
                    media_preview = "🎥 Video"
                    logger.info("Detected video in broadcast")
                elif replied_message.document:
                    media_type = 'document'
                    media_file_id = replied_message.document.file_id
                    media_caption = replied_message.caption
                    media_preview = "📄 Document"
                    logger.info("Detected document in broadcast")
                elif replied_message.animation:
                    media_type = 'animation'
                    media_file_id = replied_message.animation.file_id
                    media_caption = replied_message.caption
                    media_preview = "🎬 GIF/Animation"
                    logger.info("Detected animation in broadcast")
                
                confirm_text = f"📢 Broadcast Confirmation\n\n"
                
                if media_type:
                    confirm_text += f"Type: {media_preview}\n"
                    if media_caption:
                        confirm_text += f"Caption: {media_caption[:100]}{'...' if len(media_caption) > 100 else ''}\n"
                    confirm_text += f"\n"
                else:
                    confirm_text += f"Forwarding message to:\n"
                
                confirm_text += f"Recipients:\n"
                confirm_text += f"• {len(users)} users\n"
                confirm_text += f"• {len(groups)} groups\n"
                confirm_text += f"• Total: {total_targets} recipients\n\n"
                confirm_text += f"Confirm: /broadcast_confirm"
                
                # Store broadcast data
                if media_type:
                    context.user_data['broadcast_type'] = media_type
                    context.user_data['broadcast_media_id'] = media_file_id
                    context.user_data['broadcast_caption'] = media_caption
                else:
                    context.user_data['broadcast_message_id'] = replied_message.message_id
                    context.user_data['broadcast_chat_id'] = replied_message.chat_id
                    context.user_data['broadcast_type'] = 'forward'
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Broadcast ({media_type or 'forward'}) prepared by {update.effective_user.id}")
            
            elif context.args:
                message_text = ' '.join(context.args)
                
                # Parse inline buttons from text
                cleaned_text, reply_markup = self.parse_inline_buttons(message_text)
                
                users = self.db.get_all_users_stats()
                groups = self.db.get_all_groups()
                total_targets = len(users) + len(groups)
                
                confirm_text = f"📢 Broadcast Confirmation\n\n"
                confirm_text += f"Message: {cleaned_text[:200]}{'...' if len(cleaned_text) > 200 else ''}\n\n"
                
                if reply_markup:
                    button_count = sum(len(row) for row in reply_markup.inline_keyboard)
                    confirm_text += f"🔘 Buttons: {button_count} inline button(s)\n\n"
                
                confirm_text += f"Recipients:\n"
                confirm_text += f"• {len(users)} users\n"
                confirm_text += f"• {len(groups)} groups\n"
                confirm_text += f"• Total: {total_targets} recipients\n\n"
                confirm_text += f"Confirm: /broadcast_confirm"
                
                context.user_data['broadcast_message'] = cleaned_text
                context.user_data['broadcast_buttons'] = reply_markup
                context.user_data['broadcast_type'] = 'text'
                
                reply = await update.message.reply_text(confirm_text)
                logger.info(f"Broadcast (text) prepared by {update.effective_user.id}")
            
            else:
                reply = await update.message.reply_text(
                    "📢 Broadcast Message\n\n"
                    "Usage:\n"
                    "1. Reply to a message/media with /broadcast\n"
                    "2. /broadcast [message text]\n"
                    "3. /broadcast Message [[\"Button\",\"URL\"]]\n\n"
                    "Supported media: Photos, Videos, Documents, GIFs\n"
                    "Placeholders: {first_name}, {username}, {chat_title}, {bot_name}"
                )
                await self.auto_clean_message(update.message, reply)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /broadcast completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/broadcast',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in broadcast: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def broadcast_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and send broadcast with media, buttons, placeholders, and auto-cleanup"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Log command execution immediately
            broadcast_type = context.user_data.get('broadcast_type', 'unknown')
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/broadcast_confirm',
                details={'broadcast_type': broadcast_type, 'action': 'confirm_broadcast'},
                success=True
            )
            
            broadcast_type = context.user_data.get('broadcast_type')
            
            # Track sent messages for deletion feature
            sent_messages = {}
            if not broadcast_type:
                reply = await update.message.reply_text("❌ No broadcast found. Please use /broadcast first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("📢 Sending broadcast...")
            
            # Get ALL users and groups - SEND TO ALL STORED USERS AND GROUPS
            users = self.db.get_all_users_stats()  # Get ALL users, not just active
            groups = self.db.get_all_groups()
            
            success_count = 0
            fail_count = 0
            pm_sent = 0
            group_sent = 0
            skipped_count = 0  # Auto-removed users/groups
            
            # Create unique broadcast ID for tracking
            broadcast_id = f"broadcast_{int(time.time())}_{update.effective_user.id}"
            
            # OPTIMIZATION: Cache bot name once instead of calling for each recipient
            bot_name_cache = context.bot.first_name if context.bot.first_name else "Bot"
            
            # Get broadcast data based on type
            if broadcast_type == 'forward':
                message_id = context.user_data.get('broadcast_message_id')
                chat_id = context.user_data.get('broadcast_chat_id')
                
                # Send to users (PM)
                for user in users:
                    try:
                        sent_msg = await context.bot.copy_message(
                            chat_id=user['user_id'],
                            from_chat_id=chat_id,
                            message_id=message_id
                        )
                        sent_messages[user['user_id']] = sent_msg.message_id
                        success_count += 1
                        pm_sent += 1
                        if len(users) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was blocked by the user" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden: user is deactivated" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing user {user['user_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to user {user['user_id']}: {error_msg}")
                            fail_count += 1
                
                # Send to groups
                for group in groups:
                    try:
                        sent_msg = await context.bot.copy_message(
                            chat_id=group['chat_id'],
                            from_chat_id=chat_id,
                            message_id=message_id
                        )
                        sent_messages[group['chat_id']] = sent_msg.message_id
                        success_count += 1
                        group_sent += 1
                        if len(groups) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was kicked from the group" in error_msg or "Forbidden: bot is not a member of the group chat" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing group {group['chat_id']} - {error_msg}")
                            self.db.remove_inactive_group(group['chat_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing group {group['chat_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to group {group['chat_id']}: {error_msg}")
                            fail_count += 1
            
            elif broadcast_type in ['photo', 'video', 'document', 'animation']:
                # Media broadcast with placeholder support
                media_file_id = context.user_data.get('broadcast_media_id')
                base_caption = context.user_data.get('broadcast_caption') or ""
                reply_markup = context.user_data.get('broadcast_buttons')
                
                # Truncate caption to Telegram's 1024 character limit
                if len(base_caption) > 1024:
                    base_caption = base_caption[:1021] + "..."
                    logger.warning(f"Caption truncated to 1024 chars for broadcast")
                
                # Send to users (PM)
                for user in users:
                    try:
                        # OPTIMIZED: Apply placeholders using database data (no API call!)
                        caption = await self.replace_placeholders(
                            base_caption, user['user_id'], context, 
                            user_data=user, bot_name_cache=bot_name_cache
                        )
                        
                        # Send appropriate media type
                        if broadcast_type == 'photo':
                            sent_msg = await context.bot.send_photo(
                                chat_id=user['user_id'],
                                photo=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'video':
                            sent_msg = await context.bot.send_video(
                                chat_id=user['user_id'],
                                video=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'document':
                            sent_msg = await context.bot.send_document(
                                chat_id=user['user_id'],
                                document=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'animation':
                            sent_msg = await context.bot.send_animation(
                                chat_id=user['user_id'],
                                animation=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        
                        sent_messages[user['user_id']] = sent_msg.message_id
                        success_count += 1
                        pm_sent += 1
                        if len(users) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was blocked by the user" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden: user is deactivated" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing user {user['user_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to user {user['user_id']}: {error_msg}")
                            fail_count += 1
                
                # Send to groups
                for group in groups:
                    try:
                        # OPTIMIZED: Apply placeholders using database data (no API call!)
                        caption = await self.replace_placeholders(
                            base_caption, group['chat_id'], context, 
                            group_data=group, bot_name_cache=bot_name_cache
                        )
                        
                        # Send appropriate media type
                        if broadcast_type == 'photo':
                            sent_msg = await context.bot.send_photo(
                                chat_id=group['chat_id'],
                                photo=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'video':
                            sent_msg = await context.bot.send_video(
                                chat_id=group['chat_id'],
                                video=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'document':
                            sent_msg = await context.bot.send_document(
                                chat_id=group['chat_id'],
                                document=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        elif broadcast_type == 'animation':
                            sent_msg = await context.bot.send_animation(
                                chat_id=group['chat_id'],
                                animation=media_file_id,
                                caption=caption if caption else None,
                                reply_markup=reply_markup
                            )
                        
                        sent_messages[group['chat_id']] = sent_msg.message_id
                        success_count += 1
                        group_sent += 1
                        if len(groups) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was kicked from the group" in error_msg or "Forbidden: bot is not a member of the group chat" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing group {group['chat_id']} - {error_msg}")
                            self.db.remove_inactive_group(group['chat_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing group {group['chat_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to group {group['chat_id']}: {error_msg}")
                            fail_count += 1
            
            else:  # text broadcast with buttons and placeholders
                base_message_text = context.user_data.get('broadcast_message')
                reply_markup = context.user_data.get('broadcast_buttons')
                
                # Send to users (PM)
                for user in users:
                    try:
                        # OPTIMIZED: Apply placeholders using database data (no API call!)
                        message_text = await self.replace_placeholders(
                            base_message_text, user['user_id'], context,
                            user_data=user, bot_name_cache=bot_name_cache
                        )
                        
                        # Try sending with Markdown first, fallback to plain text if parse error
                        try:
                            sent_msg = await context.bot.send_message(
                                chat_id=user['user_id'],
                                text=message_text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                        except Exception as parse_error:
                            if "parse entities" in str(parse_error).lower() or "can't parse" in str(parse_error).lower():
                                # Fallback to plain text on Markdown parse error
                                logger.warning(f"Markdown parse error for user {user['user_id']}, falling back to plain text")
                                sent_msg = await context.bot.send_message(
                                    chat_id=user['user_id'],
                                    text=message_text,
                                    parse_mode=None,
                                    reply_markup=reply_markup
                                )
                            else:
                                raise
                        
                        sent_messages[user['user_id']] = sent_msg.message_id
                        success_count += 1
                        pm_sent += 1
                        if len(users) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was blocked by the user" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden: user is deactivated" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing user {user['user_id']} - {error_msg}")
                            self.db.remove_inactive_user(user['user_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing user {user['user_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to user {user['user_id']}: {error_msg}")
                            fail_count += 1
                
                # Send to groups
                for group in groups:
                    try:
                        # OPTIMIZED: Apply placeholders using database data (no API call!)
                        message_text = await self.replace_placeholders(
                            base_message_text, group['chat_id'], context,
                            group_data=group, bot_name_cache=bot_name_cache
                        )
                        
                        # Try sending with Markdown first, fallback to plain text if parse error
                        try:
                            sent_msg = await context.bot.send_message(
                                chat_id=group['chat_id'],
                                text=message_text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                        except Exception as parse_error:
                            if "parse entities" in str(parse_error).lower() or "can't parse" in str(parse_error).lower():
                                # Fallback to plain text on Markdown parse error
                                logger.warning(f"Markdown parse error for group {group['chat_id']}, falling back to plain text")
                                sent_msg = await context.bot.send_message(
                                    chat_id=group['chat_id'],
                                    text=message_text,
                                    parse_mode=None,
                                    reply_markup=reply_markup
                                )
                            else:
                                raise
                        
                        sent_messages[group['chat_id']] = sent_msg.message_id
                        success_count += 1
                        group_sent += 1
                        if len(groups) > 20:
                            await asyncio.sleep(0.03)
                    except Exception as e:
                        error_msg = str(e)
                        # CONSTRAINED AUTO-CLEANUP: Only delete on specific permission errors
                        if "Forbidden: bot was kicked from the group" in error_msg or "Forbidden: bot is not a member of the group chat" in error_msg:
                            logger.info(f"AUTO-CLEANUP: Removing group {group['chat_id']} - {error_msg}")
                            self.db.remove_inactive_group(group['chat_id'])
                            skipped_count += 1
                        elif "Forbidden" in error_msg:
                            # Generic Forbidden - don't delete, just log
                            logger.warning(f"SAFETY: Not removing group {group['chat_id']} - error was: {error_msg}")
                            fail_count += 1
                        else:
                            logger.warning(f"Failed to send to group {group['chat_id']}: {error_msg}")
                            fail_count += 1
            
            # Store sent messages in database for delbroadcast feature
            if sent_messages:
                self.db.save_broadcast(broadcast_id, update.effective_user.id, sent_messages)
                logger.info(f"Saved broadcast {broadcast_id} to database with {len(sent_messages)} messages")
            
            # Log broadcast to database for historical tracking
            total_targets = len(users) + len(groups)
            message_text = context.user_data.get('broadcast_message', '')[:500] if broadcast_type == 'text' else f"[{broadcast_type.upper()} BROADCAST]"
            self.db.log_broadcast(
                admin_id=update.effective_user.id,
                message_text=message_text,
                total_targets=total_targets,
                sent_count=success_count,
                failed_count=fail_count,
                skipped_count=skipped_count
            )
            
            # Build result message
            result_text = f"✅ Broadcast completed!\n\n"
            result_text += f"📱 PM Sent: {pm_sent}\n"
            result_text += f"👥 Groups Sent: {group_sent}\n"
            result_text += f"━━━━━━━━━━━━━━━\n"
            result_text += f"✅ Total Sent: {success_count}\n"
            result_text += f"❌ Failed: {fail_count}\n"
            if skipped_count > 0:
                result_text += f"🗑️ Auto-Removed: {skipped_count}"
            
            await status.edit_text(result_text)
            
            logger.info(f"Broadcast completed by {update.effective_user.id}: {pm_sent} PMs, {group_sent} groups ({success_count} total, {fail_count} failed, {skipped_count} auto-removed)")
            
            # Clear broadcast data
            context.user_data.pop('broadcast_message', None)
            context.user_data.pop('broadcast_message_id', None)
            context.user_data.pop('broadcast_chat_id', None)
            context.user_data.pop('broadcast_type', None)
            context.user_data.pop('broadcast_media_id', None)
            context.user_data.pop('broadcast_caption', None)
            context.user_data.pop('broadcast_buttons', None)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /broadcast_confirm completed in {response_time}ms - sent: {success_count}, failed: {fail_count}")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/broadcast_confirm',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in broadcast_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error sending broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def delbroadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete latest broadcast from all groups/users - Works from anywhere!"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Get latest broadcast from database
            broadcast_data = self.db.get_latest_broadcast()
            target_count = len(broadcast_data['message_data']) if broadcast_data and 'message_data' in broadcast_data else 0
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/delbroadcast',
                details={'target_count': target_count},
                success=True
            )
            
            if not broadcast_data:
                reply = await update.message.reply_text(
                    "❌ No recent broadcast found\n\n"
                    "Either no broadcast was sent yet or it was already deleted."
                )
                await self.auto_clean_message(update.message, reply)
                return
            
            broadcast_messages = broadcast_data['message_data']
            
            if not broadcast_messages:
                reply = await update.message.reply_text("❌ Broadcast data not found")
                await self.auto_clean_message(update.message, reply)
                return
            
            # Confirm deletion
            confirm_text = (
                "🗑️ Delete Broadcast Confirmation\n\n"
                f"This will delete the latest broadcast from {len(broadcast_messages)} chats.\n\n"
                "⚠️ Note: Some deletions may fail if:\n"
                "• Bot is not admin in groups\n"
                "• Message is older than 48 hours\n\n"
                "Confirm: /delbroadcast_confirm"
            )
            
            reply = await update.message.reply_text(confirm_text)
            logger.info(f"Broadcast deletion prepared by {update.effective_user.id} for {len(broadcast_messages)} chats")
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /delbroadcast completed in {response_time}ms")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/delbroadcast',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in delbroadcast: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error preparing broadcast deletion")
            await self.auto_clean_message(update.message, reply)
    
    async def delbroadcast_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and execute broadcast deletion - Optimized for instant deletion"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            # Log command execution immediately
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/delbroadcast_confirm',
                details={'action': 'confirm_deletion'},
                success=True
            )
            
            # Get latest broadcast data from database
            broadcast_data = self.db.get_latest_broadcast()
            
            if not broadcast_data:
                reply = await update.message.reply_text("❌ No broadcast found. Please use /delbroadcast first.")
                await self.auto_clean_message(update.message, reply)
                return
            
            broadcast_id = broadcast_data['broadcast_id']
            broadcast_messages = broadcast_data['message_data']
            
            if not broadcast_messages:
                reply = await update.message.reply_text("❌ Broadcast data not found")
                await self.auto_clean_message(update.message, reply)
                return
            
            status = await update.message.reply_text("🗑️ Deleting broadcast instantly...")
            
            success_count = 0
            fail_count = 0
            
            # Delete from all chats instantly
            for chat_id, message_id in broadcast_messages.items():
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    success_count += 1
                except Exception as e:
                    logger.debug(f"Failed to delete from chat {chat_id}: {e}")
                    fail_count += 1
            
            await status.edit_text(
                f"✅ Broadcast deleted instantly!\n\n"
                f"• Deleted: {success_count}\n"
                f"• Failed: {fail_count}\n\n"
                f"💡 Failed deletions occur when bot lacks permissions or message is too old."
            )
            
            logger.info(f"Broadcast deletion by {update.effective_user.id}: {success_count} deleted, {fail_count} failed")
            
            # Clear broadcast data from database
            self.db.delete_broadcast(broadcast_id)
            
            # Calculate response time at end
            response_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Command /delbroadcast_confirm completed in {response_time}ms - deleted: {success_count}, failed: {fail_count}")
        
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/delbroadcast_confirm',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in delbroadcast_confirm: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error deleting broadcast")
            await self.auto_clean_message(update.message, reply)
    
    async def performance_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show live performance metrics dashboard"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                chat_title=getattr(update.effective_chat, 'title', None),
                command='/performance',
                success=True
            )
            
            loading_msg = await update.message.reply_text("📊 Loading performance metrics...")
            
            hours = 24
            if context.args and context.args[0].isdigit():
                hours = int(context.args[0])
                hours = min(hours, 168)
            
            perf_summary = self.db.get_performance_summary(hours=hours)
            response_trends = self.db.get_response_time_trends(hours=hours)
            api_calls = self.db.get_api_call_counts(hours=hours)
            memory_history = self.db.get_memory_usage_history(hours=hours)
            
            import psutil
            import os
            process = psutil.Process(os.getpid())
            current_memory_mb = process.memory_info().rss / 1024 / 1024
            
            perf_message = f"📊 *Performance Metrics Dashboard*\n"
            perf_message += f"🕒 *Period:* Last {hours} hours\n\n"
            
            perf_message += f"⚡ *Response Times:*\n"
            perf_message += f"• Average: {perf_summary['avg_response_time']:.2f}ms\n"
            if response_trends:
                recent_avg = sum(t['avg_response_time'] for t in response_trends[:3]) / min(3, len(response_trends))
                perf_message += f"• Recent (3h): {recent_avg:.2f}ms\n"
            perf_message += f"\n"
            
            perf_message += f"📞 *API Calls:*\n"
            perf_message += f"• Total: {perf_summary['total_api_calls']:,}\n"
            if api_calls:
                top_api = sorted(api_calls.items(), key=lambda x: x[1], reverse=True)[:3]
                for api_name, count in top_api:
                    if api_name:
                        perf_message += f"• {api_name}: {count:,}\n"
            perf_message += f"\n"
            
            perf_message += f"💾 *Memory Usage:*\n"
            perf_message += f"• Current: {current_memory_mb:.2f} MB\n"
            if perf_summary['avg_memory_mb'] > 0:
                perf_message += f"• Average: {perf_summary['avg_memory_mb']:.2f} MB\n"
            if memory_history:
                max_mem = max(m['memory_usage_mb'] for m in memory_history)
                min_mem = min(m['memory_usage_mb'] for m in memory_history)
                perf_message += f"• Peak: {max_mem:.2f} MB\n"
                perf_message += f"• Min: {min_mem:.2f} MB\n"
            perf_message += f"\n"
            
            perf_message += f"❌ *Error Rate:*\n"
            perf_message += f"• Rate: {perf_summary['error_rate']:.2f}%\n"
            perf_message += f"\n"
            
            perf_message += f"🟢 *Uptime:*\n"
            perf_message += f"• Status: {perf_summary['uptime_percent']:.1f}%\n"
            perf_message += f"\n"
            
            if response_trends:
                perf_message += f"📈 *Response Time Trends:*\n"
                for trend in response_trends[:5]:
                    hour = trend['hour'].split(' ')[1][:5]
                    perf_message += f"• {hour}: {trend['avg_response_time']:.1f}ms ({trend['count']} ops)\n"
                perf_message += f"\n"
            
            perf_message += f"💡 *Commands:*\n"
            perf_message += f"• /performance [hours] - Custom time period\n"
            perf_message += f"• Max 168 hours (7 days)\n"
            
            await loading_msg.edit_text(perf_message, parse_mode=ParseMode.MARKDOWN)
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/performance dashboard shown in {response_time}ms")
            
            self.db.log_performance_metric(
                metric_type='response_time',
                metric_name='/performance',
                value=response_time,
                unit='ms'
            )
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_activity(
                activity_type='error',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                command='/performance',
                details={'error': str(e)},
                success=False,
                response_time_ms=response_time
            )
            logger.error(f"Error in performance_stats: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error loading performance metrics")
            await self.auto_clean_message(update.message, reply)
    
    async def devstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comprehensive developer statistics dashboard"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            loading_msg = await update.message.reply_text("📊 Loading comprehensive dev stats...")
            
            import psutil
            from datetime import datetime, timedelta
            
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if hasattr(self.quiz_manager, 'bot_start_time'):
                uptime_seconds = (datetime.now() - self.quiz_manager.bot_start_time).total_seconds()
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
            
            total_users = len(self.db.get_all_users())
            total_groups = len(self.db.get_all_groups())
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
                elif activity_type == 'broadcast':
                    activity_feed += f"• {time_ago}: Broadcast sent\n"
                elif activity_type == 'error':
                    activity_feed += f"• {time_ago}: Error logged\n"
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

━━━━━━━━━━━━━━━━━━━
🕐 Generated in {(time.time() - start_time)*1000:.0f}ms"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="devstats_refresh")],
                [
                    InlineKeyboardButton("📊 Full Activity", callback_data="devstats_activity"),
                    InlineKeyboardButton("⚡ Performance", callback_data="devstats_performance")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(
                devstats_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/devstats shown in {response_time}ms")
            
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                details={'command': 'devstats'},
                success=True,
                response_time_ms=response_time
            )
            
        except Exception as e:
            logger.error(f"Error in devstats: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error loading dev statistics")
            await self.auto_clean_message(update.message, reply)
    
    async def activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Live activity stream with filtering and pagination"""
        start_time = time.time()
        try:
            if not await self.check_access(update):
                await self.send_unauthorized_message(update)
                return
            
            activity_type = context.args[0] if context.args else 'all'
            page = int(context.args[1]) if len(context.args) > 1 else 1
            
            valid_types = ['all', 'command', 'quiz_sent', 'quiz_answered', 'broadcast', 'error']
            if activity_type not in valid_types:
                activity_type = 'all'
            
            limit = 50
            offset = (page - 1) * limit
            
            loading_msg = await update.message.reply_text(f"📜 Loading activity stream ({activity_type})...")
            
            if activity_type == 'all':
                activities = self.db.get_recent_activities(limit)
            else:
                activities = self.db.get_recent_activities(limit, activity_type)
            
            if not activities:
                await loading_msg.edit_text(f"📜 No activities found for type: {activity_type}")
                return
            
            activity_text = f"""📜 **Live Activity Stream**
Type: {activity_type.upper()}
━━━━━━━━━━━━━━━━━━━

"""
            
            for activity in activities[:50]:
                time_ago = self.db.format_relative_time(activity['timestamp'])
                activity_type_str = activity['activity_type']
                user_id = activity.get('user_id')
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
📊 Showing {len(activities[:50])} activities
🕐 Loaded in {(time.time() - start_time)*1000:.0f}ms"""
            
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
            
            await loading_msg.edit_text(
                activity_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
            response_time = int((time.time() - start_time) * 1000)
            logger.info(f"/activity shown in {response_time}ms")
            
            self.db.log_activity(
                activity_type='command',
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                username=update.effective_user.username,
                details={'command': 'activity', 'filter': activity_type},
                success=True,
                response_time_ms=response_time
            )
            
        except Exception as e:
            logger.error(f"Error in activity: {e}", exc_info=True)
            reply = await update.message.reply_text("❌ Error loading activity stream")
            await self.auto_clean_message(update.message, reply)
