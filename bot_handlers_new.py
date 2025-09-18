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
        try:
            if not await self.check_cooldown(update.effective_user.id, "quiz"):
                await update.message.reply_text("⏳ Please wait a moment before starting another quiz!")
                return

            loading_message = await update.message.reply_text("🎯 Preparing your quiz...")

            try:
                await self.send_quiz(update.effective_chat.id, context)
                await loading_message.delete()
            except Exception as e:
                logger.error(f"Error in quiz command: {e}")
                await loading_message.edit_text("❌ Oops! Something went wrong. Try /quiz again!")

        except Exception as e:
            logger.error(f"Error in quiz command: {e}")
            await self.send_friendly_error_message(update.effective_chat.id, context)

    async def send_quiz(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a quiz with improved formatting and error handling"""
        try:
            # Clean up previous quiz
            try:
                chat_history = self.command_history.get(chat_id, [])
                if chat_history:
                    last_quiz = next((cmd for cmd in reversed(chat_history) if cmd.startswith("/quiz_")), None)
                    if last_quiz:
                        msg_id = int(last_quiz.split("_")[1])
                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        logger.info(f"Deleted previous quiz message {msg_id} in chat {chat_id}")
            except Exception as e:
                logger.warning(f"Failed to delete previous quiz: {e}")

            # Get a random question for this specific chat
            question = self.quiz_manager.get_random_question(chat_id)
            if not question:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📝 We're preparing more exciting questions!\nTry again in a moment! ✨"
                )
                return

            # Clean question text
            question_text = question['question'].strip()
            if question_text.startswith('/addquiz'):
                question_text = question_text[len('/addquiz'):].strip()

            # Send the quiz with better formatting
            message = await context.bot.send_poll(
                chat_id=chat_id,
                question=f"🎯 {question_text}",
                options=question['options'],
                type=Poll.QUIZ,
                correct_option_id=question['correct_answer'],
                is_anonymous=False,
                explanation="💡 Keep learning and having fun!",
                explanation_parse_mode=ParseMode.MARKDOWN
            )

            if message and message.poll:
                poll_data = {
                    'chat_id': chat_id,
                    'correct_option_id': question['correct_answer'],
                    'user_answers': {},
                    'poll_id': message.poll.id,
                    'question': question_text,
                    'timestamp': datetime.now().isoformat()
                }
                context.bot_data[f"poll_{message.poll.id}"] = poll_data
                self.command_history[chat_id].append(f"/quiz_{message.message_id}")

            logger.info(f"Successfully sent quiz to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error sending quiz: {str(e)}")
            await self.send_friendly_error_message(chat_id, context)