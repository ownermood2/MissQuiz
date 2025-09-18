import json
import random
import os
import logging
import traceback
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class QuizManager:
    def __init__(self):
        """Initialize the quiz manager with proper data structures and caching"""
        # Initialize file paths
        self.questions_file = "data/questions.json"
        self.scores_file = "data/scores.json"
        self.active_chats_file = "data/active_chats.json"
        self.stats_file = "data/user_stats.json"

        # Initialize data attributes first
        self.questions = []
        self.scores = {}
        self.active_chats = []
        self.stats = {}

        # Initialize caching structures
        self._cached_questions = None
        self._cached_leaderboard = None
        self._leaderboard_cache_time = None
        self._cache_duration = timedelta(minutes=5)

        # Initialize tracking structures
        self.recent_questions = defaultdict(lambda: deque(maxlen=50))  # Store last 50 questions per chat
        self.last_question_time = defaultdict(dict)  # Track when each question was last asked in each chat
        self.available_questions = defaultdict(list)  # Track available questions per chat

        # Initialize basic data
        self._initialize_files()
        self._last_save = datetime.now()
        self._save_interval = timedelta(minutes=5)

        # Load data after all structures are initialized
        self.load_data()

    def _initialize_files(self):
        """Initialize data files with proper error handling"""
        try:
            os.makedirs("data", exist_ok=True)
            default_files = {
                self.questions_file: [],
                self.scores_file: {},
                self.active_chats_file: [],
                self.stats_file: {}
            }
            for file_path, default_data in default_files.items():
                if not os.path.exists(file_path):
                    with open(file_path, 'w') as f:
                        json.dump(default_data, f)
        except Exception as e:
            logger.error(f"Error initializing files: {e}")
            raise

    def load_data(self):
        """Load all data with proper error handling"""
        try:
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)

            # Initialize questions with defaults if file is empty or corrupted
            try:
                if not os.path.exists(self.questions_file):
                    with open(self.questions_file, 'w') as f:
                        json.dump([], f)
                        logger.info("Created new questions file")

                with open(self.questions_file, 'r') as f:
                    raw_data = json.load(f)
                    if isinstance(raw_data, dict) and 'questions' in raw_data:
                        raw_questions = raw_data['questions']
                    elif isinstance(raw_data, list):
                        raw_questions = raw_data
                    else:
                        raw_questions = []
                        logger.warning("Invalid questions format, using empty list")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Questions file error: {e}, initializing with defaults")
                raw_questions = []

            # Clean up existing questions
            self.questions = []
            for q in raw_questions:
                try:
                    if not isinstance(q, dict):
                        continue

                    question = q.get('question', '').strip()
                    if not question:
                        continue

                    if question.startswith('/addquiz'):
                        question = question[len('/addquiz'):].strip()

                    correct_answer = q.get('correct_answer', 0)
                    if isinstance(correct_answer, int) and correct_answer > 0:
                        correct_answer = correct_answer - 1

                    options = q.get('options', [])
                    if len(options) == 4:
                        self.questions.append({
                            'question': question,
                            'options': options,
                            'correct_answer': correct_answer
                        })
                except Exception as e:
                    logger.error(f"Error processing question: {e}")
                    continue

            # Load other data files with proper initialization
            for file_path, default_value, attr_name in [
                (self.scores_file, {}, 'scores'),
                (self.active_chats_file, [], 'active_chats'),
                (self.stats_file, {}, 'stats')
            ]:
                try:
                    if not os.path.exists(file_path):
                        with open(file_path, 'w') as f:
                            json.dump(default_value, f)
                            logger.info(f"Created new file: {file_path}")

                    with open(file_path, 'r') as f:
                        setattr(self, attr_name, json.load(f))
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    logger.warning(f"Error loading {file_path}: {e}, using defaults")
                    setattr(self, attr_name, default_value)

            # Reset tracking structures
            self.recent_questions.clear()
            self.last_question_time.clear()
            self.available_questions.clear()

            # Clear caches
            self._cached_questions = None
            self._cached_leaderboard = None
            self._leaderboard_cache_time = None

            # Force save to ensure clean data
            self.save_data(force=True)

            logger.info(f"Successfully loaded and cleaned {len(self.questions)} questions")
            logger.info(f"Active chats: {len(self.active_chats)}")
            logger.info(f"Active users with stats: {len(self.stats)}")
            logger.info(f"Users with scores: {len(self.scores)}")

        except Exception as e:
            logger.error(f"Critical error loading data: {str(e)}\n{traceback.format_exc()}")
            raise

    def save_data(self, force=False):
        """Save data with throttling to prevent excessive writes"""
        current_time = datetime.now()
        if not force and current_time - self._last_save < self._save_interval:
            return

        try:
            # Save questions file with proper JSON formatting
            with open(self.questions_file, 'w') as f:
                json.dump(self.questions, f, indent=2)
                logger.info(f"Saved {len(self.questions)} questions to file")

            # Save other data files
            with open(self.scores_file, 'w') as f:
                json.dump(self.scores, f, indent=2)
            with open(self.active_chats_file, 'w') as f:
                json.dump(self.active_chats, f, indent=2)
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)

            self._last_save = current_time
            logger.info(f"All data saved successfully. Questions count: {len(self.questions)}")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}\n{traceback.format_exc()}")
            raise

    def _init_user_stats(self, user_id: str) -> None:
        """Initialize stats for a new user with enhanced tracking"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        self.stats[user_id] = {
            'total_quizzes': 0,
            'correct_answers': 0,
            'current_streak': 0,
            'longest_streak': 0,
            'last_correct_date': None,
            'category_scores': {},
            'daily_activity': {
                current_date: {
                    'attempts': 0,
                    'correct': 0
                }
            },
            'last_quiz_date': current_date,
            'last_activity_date': current_date,
            'join_date': current_date,
            'groups': {},
            'private_chat_activity': {
                'total_messages': 0,
                'last_active': current_date
            }
        }

    def get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive stats for a user"""
        try:
            user_id_str = str(user_id)
            current_date = datetime.now().strftime('%Y-%m-%d')

            logger.info(f"Attempting to get stats for user {user_id}")
            logger.debug(f"Current stats data: {self.stats.get(user_id_str, 'Not Found')}")

            # Initialize stats if user doesn't exist
            if user_id_str not in self.stats:
                logger.info(f"Initializing new stats for user {user_id}")
                self._init_user_stats(user_id_str)
                self.save_data(force=True)

                # Return initial stats
                return {
                    'total_quizzes': 0,
                    'correct_answers': 0,
                    'success_rate': 0.0,
                    'today_quizzes': 0,
                    'week_quizzes': 0,
                    'month_quizzes': 0,
                    'current_score': 0,
                    'current_streak': 0,
                    'longest_streak': 0
                }

            stats = self.stats[user_id_str]
            logger.debug(f"Retrieved raw stats: {stats}")

            # Ensure today's activity exists
            if current_date not in stats['daily_activity']:
                stats['daily_activity'][current_date] = {'attempts': 0, 'correct': 0}
                self.save_data()

            # Get today's stats
            today_stats = stats['daily_activity'].get(current_date, {'attempts': 0, 'correct': 0})

            # Calculate weekly stats
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
            week_quizzes = sum(
                day_stats['attempts']
                for date, day_stats in stats['daily_activity'].items()
                if date >= week_start
            )

            # Calculate monthly stats
            month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            month_quizzes = sum(
                day_stats['attempts']
                for date, day_stats in stats['daily_activity'].items()
                if date >= month_start
            )

            # Calculate success rate
            if stats['total_quizzes'] > 0:
                success_rate = (stats['correct_answers'] / stats['total_quizzes']) * 100
            else:
                success_rate = 0.0

            # Sync with scores data
            score = self.scores.get(user_id_str, 0)
            if score != stats['correct_answers']:
                logger.info(f"Syncing score for user {user_id}: {score} != {stats['correct_answers']}")
                stats['correct_answers'] = score
                stats['total_quizzes'] = max(stats['total_quizzes'], score)
                self.save_data(force=True)

            formatted_stats = {
                'total_quizzes': stats['total_quizzes'],
                'correct_answers': stats['correct_answers'],
                'success_rate': round(success_rate, 1),
                'current_score': stats['correct_answers'],
                'today_quizzes': today_stats['attempts'],
                'week_quizzes': week_quizzes,
                'month_quizzes': month_quizzes,
                'current_streak': stats.get('current_streak', 0),
                'longest_streak': stats.get('longest_streak', 0)
            }

            logger.info(f"Successfully retrieved stats for user {user_id}: {formatted_stats}")
            return formatted_stats

        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {str(e)}\n{traceback.format_exc()}")
            logger.error(f"Raw stats data: {self.stats.get(str(user_id), 'Not Found')}")
            return None

    def get_group_leaderboard(self, chat_id: int) -> Dict:
        """Get group-specific leaderboard with detailed analytics"""
        chat_id_str = str(chat_id)
        current_date = datetime.now()
        today = current_date.strftime('%Y-%m-%d')
        week_start = (current_date - timedelta(days=current_date.weekday())).strftime('%Y-%m-%d')
        month_start = current_date.replace(day=1).strftime('%Y-%m-%d')

        # Initialize counters and sets
        total_group_quizzes = 0
        total_correct_answers = 0
        active_users = {
            'today': set(),
            'week': set(),
            'month': set(),
            'total': set()
        }
        leaderboard = []

        # Process user stats
        for user_id, stats in self.stats.items():
            if chat_id_str in stats.get('groups', {}):
                group_stats = stats['groups'][chat_id_str]
                active_users['total'].add(user_id)

                # Update activity counters
                last_activity = group_stats.get('last_activity_date')
                if last_activity:
                    if last_activity == today:
                        active_users['today'].add(user_id)
                    if last_activity >= week_start:
                        active_users['week'].add(user_id)
                    if last_activity >= month_start:
                        active_users['month'].add(user_id)

                # Calculate user statistics
                user_total_attempts = group_stats.get('total_quizzes', 0)
                user_correct_answers = group_stats.get('correct_answers', 0)
                total_group_quizzes += user_total_attempts
                total_correct_answers += user_correct_answers

                # Get daily activity stats
                daily_stats = group_stats.get('daily_activity', {})
                today_stats = daily_stats.get(today, {'attempts': 0, 'correct': 0})

                leaderboard.append({
                    'user_id': int(user_id),
                    'total_attempts': user_total_attempts,
                    'correct_answers': user_correct_answers,
                    'wrong_answers': user_total_attempts - user_correct_answers,
                    'accuracy': round((user_correct_answers / user_total_attempts * 100) if user_total_attempts > 0 else 0, 1),
                    'score': group_stats.get('score', 0),
                    'current_streak': group_stats.get('current_streak', 0),
                    'longest_streak': group_stats.get('longest_streak', 0),
                    'today_attempts': today_stats['attempts'],
                    'today_correct': today_stats['correct'],
                    'last_active': group_stats.get('last_activity_date', 'Never')
                })

        # Sort leaderboard by score and accuracy
        leaderboard.sort(key=lambda x: (x['score'], x['accuracy']), reverse=True)
        group_accuracy = (total_correct_answers / total_group_quizzes * 100) if total_group_quizzes > 0 else 0

        return {
            'total_quizzes': total_group_quizzes,
            'total_correct': total_correct_answers,
            'group_accuracy': round(group_accuracy, 1),
            'active_users': {
                'today': len(active_users['today']),
                'week': len(active_users['week']),
                'month': len(active_users['month']),
                'total': len(active_users['total'])
            },
            'leaderboard': leaderboard[:10]  # Top 10 performers
        }

    def record_group_attempt(self, user_id: int, chat_id: int, is_correct: bool) -> None:
        """Record a quiz attempt for a user in a specific group with timestamp"""
        try:
            user_id_str = str(user_id)
            chat_id_str = str(chat_id)
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Initialize user stats if needed
            if user_id_str not in self.stats:
                self._init_user_stats(user_id_str)

            stats = self.stats[user_id_str]

            # Initialize group stats if needed
            if 'groups' not in stats:
                stats['groups'] = {}

            if chat_id_str not in stats['groups']:
                stats['groups'][chat_id_str] = {
                    'total_quizzes': 0,
                    'correct_answers': 0,
                    'score': 0,
                    'last_activity_date': None,
                    'daily_activity': {},
                    'current_streak': 0,
                    'longest_streak': 0,
                    'last_correct_date': None
                }

            group_stats = stats['groups'][chat_id_str]
            group_stats['total_quizzes'] += 1
            group_stats['last_activity_date'] = current_date

            # Update daily activity
            if current_date not in group_stats['daily_activity']:
                group_stats['daily_activity'][current_date] = {'attempts': 0, 'correct': 0}

            group_stats['daily_activity'][current_date]['attempts'] += 1

            if is_correct:
                group_stats['correct_answers'] += 1
                group_stats['score'] += 1
                group_stats['daily_activity'][current_date]['correct'] += 1

                # Update streak
                if group_stats.get('last_correct_date') == (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
                    group_stats['current_streak'] += 1
                else:
                    group_stats['current_streak'] = 1

                group_stats['longest_streak'] = max(group_stats['current_streak'], group_stats['longest_streak'])
                group_stats['last_correct_date'] = current_date
            else:
                group_stats['current_streak'] = 0

            # Also record the attempt in user's general stats
            self.record_attempt(user_id, is_correct)
            self.save_data()

        except Exception as e:
            logger.error(f"Error recording group attempt: {e}")
            raise

    def _initialize_available_questions(self, chat_id: int):
        """Initialize or reset available questions for a chat"""
        self.available_questions[chat_id] = list(range(len(self.questions)))
        random.shuffle(self.available_questions[chat_id])
        logger.info(f"Initialized question pool for chat {chat_id} with {len(self.questions)} questions")

    def get_random_question(self, chat_id: int = None) -> Optional[Dict[str, Any]]:
        """Get a random question avoiding recent ones with improved tracking"""
        try:
            if not self.questions:
                return None

            # If no chat_id provided, return completely random
            if not chat_id:
                return random.choice(self.questions)

            # Initialize available questions if needed
            if chat_id not in self.available_questions or not self.available_questions[chat_id]:
                logger.info(f"Initializing question pool for chat {chat_id}")
                self._initialize_available_questions(chat_id)

            # Get the next question index from the shuffled list
            question_index = self.available_questions[chat_id].pop()
            question = self.questions[question_index]

            # Track this question
            self.recent_questions[chat_id].append(question['question'])
            self.last_question_time[chat_id][question['question']] = datetime.now()

            # If we've used all questions, reset the pool
            if not self.available_questions[chat_id]:
                logger.info(f"Reset question pool for chat {chat_id}")
                self._initialize_available_questions(chat_id)

            logger.info(f"Selected question {question_index} for chat {chat_id}. "
                       f"Question text: {question['question'][:30]}... "
                       f"Remaining questions: {len(self.available_questions[chat_id])}")
            return question

        except Exception as e:
            logger.error(f"Error in get_random_question: {e}\n{traceback.format_exc()}")
            # Fallback to completely random selection
            return random.choice(self.questions)

    def get_leaderboard(self) -> List[Dict]:
        """Get global leaderboard with caching"""
        current_time = datetime.now()

        # Force refresh cache if it's stale
        if (self._cached_leaderboard is None or
            self._leaderboard_cache_time is None or
            current_time - self._leaderboard_cache_time > self._cache_duration):

            leaderboard = []
            current_date = current_time.strftime('%Y-%m-%d')

            for user_id, stats in self.stats.items():
                total_attempts = stats['total_quizzes']
                correct_answers = stats['correct_answers']

                # Get today's performance
                today_stats = stats['daily_activity'].get(current_date, {'attempts': 0, 'correct': 0})

                accuracy = (correct_answers / total_attempts * 100) if total_attempts > 0 else 0

                leaderboard.append({
                    'user_id': int(user_id),
                    'total_attempts': total_attempts,
                    'correct_answers': correct_answers,
                    'wrong_answers': total_attempts - correct_answers,
                    'accuracy': round(accuracy, 1),
                    'score': self.get_score(int(user_id)),
                    'today_attempts': today_stats['attempts'],
                    'today_correct': today_stats['correct'],
                    'current_streak': stats.get('current_streak', 0),
                    'longest_streak': stats.get('longest_streak', 0)
                })

            # Sort by score, then accuracy, then streak
            leaderboard.sort(key=lambda x: (-x['score'], -x['accuracy'], -x['current_streak']))
            self._cached_leaderboard = leaderboard[:10]
            self._leaderboard_cache_time = current_time
            logger.info(f"Refreshed leaderboard cache with {len(leaderboard)} entries")

        return self._cached_leaderboard

    def record_attempt(self, user_id: int, is_correct: bool, category: str = None):
        """Record a quiz attempt for a user in real-time"""
        try:
            user_id_str = str(user_id)
            current_date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"Recording attempt for user {user_id}: correct={is_correct}")

            # Initialize user stats if needed
            if user_id_str not in self.stats:
                self._init_user_stats(user_id_str)

            stats = self.stats[user_id_str]
            stats['total_quizzes'] += 1
            stats['last_quiz_date'] = current_date

            # Initialize today's activity if not exists
            if current_date not in stats['daily_activity']:
                stats['daily_activity'][current_date] = {'attempts': 0, 'correct': 0}

            # Update daily activity
            stats['daily_activity'][current_date]['attempts'] += 1

            if is_correct:
                stats['correct_answers'] += 1
                stats['daily_activity'][current_date]['correct'] += 1

                # Update streak
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                if stats.get('last_correct_date') == yesterday:
                    stats['current_streak'] += 1
                else:
                    stats['current_streak'] = 1

                stats['longest_streak'] = max(stats['current_streak'], stats.get('longest_streak', 0))
                stats['last_correct_date'] = current_date

                # Update score
                if user_id_str not in self.scores:
                    self.scores[user_id_str] = 0
                self.scores[user_id_str] += 1

                # Update category scores if provided
                if category:
                    if 'category_scores' not in stats:
                        stats['category_scores'] = {}
                    if category not in stats['category_scores']:
                        stats['category_scores'][category] = 0
                    stats['category_scores'][category] += 1
            else:
                stats['current_streak'] = 0

            # Save immediately for real-time tracking
            self.save_data(force=True)
            logger.info(f"Successfully recorded attempt for user {user_id}: score={self.scores.get(user_id_str)}, streak={stats['current_streak']}")

        except Exception as e:
            logger.error(f"Error recording attempt for user {user_id}: {str(e)}\n{traceback.format_exc()}")
            raise

    def add_questions(self, questions_data: List[Dict]) -> Dict:
        """Add multiple questions with validation and duplicate detection"""
        stats = {
            'added': 0,
            'rejected': {
                'duplicates': 0,
                'invalid_format': 0,
                'invalid_options': 0
            },
            'errors': []
        }

        if len(questions_data) > 500:
            stats['errors'].append("Maximum 500 questions allowed at once")
            return stats

        logger.info(f"Starting to add {len(questions_data)} questions. Current count: {len(self.questions)}")
        added_questions = []

        for question_data in questions_data:
            try:
                # Basic format validation
                if not all(key in question_data for key in ['question', 'options', 'correct_answer']):
                    logger.warning(f"Invalid format for question: {question_data}")
                    stats['rejected']['invalid_format'] += 1
                    stats['errors'].append(f"Invalid format for question: {question_data.get('question', 'Unknown')}")
                    continue

                # Clean up question text - remove /addquiz prefix and extra whitespace
                question = question_data['question'].strip()
                if question.startswith('/addquiz'):
                    question = question[len('/addquiz'):].strip()

                options = [opt.strip() for opt in question_data['options']]

                # Convert correct_answer to zero-based index if needed
                correct_answer = question_data['correct_answer']
                if isinstance(correct_answer, str):
                    try:
                        correct_answer = int(correct_answer)
                    except ValueError:
                        logger.warning(f"Invalid correct_answer format: {correct_answer}")
                        stats['rejected']['invalid_format'] += 1
                        continue

                if isinstance(correct_answer, int) and correct_answer > 0:
                    correct_answer = correct_answer - 1

                # Validate question text
                if not question or len(question) < 5:
                    logger.warning(f"Question text too short: {question}")
                    stats['rejected']['invalid_format'] += 1
                    stats['errors'].append(f"Question text too short: {question}")
                    continue

                # Check for duplicates
                if any(q['question'].lower() == question.lower() for q in self.questions):
                    logger.warning(f"Duplicate question detected: {question}")
                    stats['rejected']['duplicates'] += 1
                    stats['errors'].append(f"Duplicate question: {question}")
                    continue

                # Validate options
                if len(options) != 4 or not all(opt for opt in options):
                    logger.warning(f"Invalid options for question: {question}")
                    stats['rejected']['invalid_options'] += 1
                    stats['errors'].append(f"Invalid options for question: {question}")
                    continue

                # Validate correct answer index
                if not isinstance(correct_answer, int) or not (0 <= correct_answer < 4):
                    logger.warning(f"Invalid correct answer index for question: {question}")
                    stats['rejected']['invalid_format'] += 1
                    stats['errors'].append(f"Invalid correct answer index for question: {question}")
                    continue

                # Add valid question
                question_obj = {
                    'question': question,
                    'options': options,
                    'correct_answer': correct_answer
                }
                added_questions.append(question_obj)
                stats['added'] += 1
                logger.info(f"Added question: {question}")

            except Exception as e:
                logger.error(f"Error processing question: {str(e)}\n{traceback.format_exc()}")
                stats['errors'].append(f"Unexpected error: {str(e)}")

        if stats['added'] > 0:
            # Update questions list with new questions
            self.questions.extend(added_questions)
            # Force save immediately after adding questions
            self.save_data(force=True)
            logger.info(f"Added {stats['added']} questions. New total: {len(self.questions)}")

        return stats

    def delete_question(self, index: int):
        if 0 <= index < len(self.questions):
            self.questions.pop(index)
            self.save_data()

    def get_all_questions(self) -> List[Dict]:
        """Get all questions with proper loading"""
        try:
            # Reload questions from file to ensure we have latest data
            with open(self.questions_file, 'r') as f:
                self.questions = json.load(f)
            logger.info(f"Loaded {len(self.questions)} questions from file")
            return self.questions
        except Exception as e:
            logger.error(f"Error loading questions: {e}")
            return self.questions  # Return cached questions as fallback

    def increment_score(self, user_id: int):
        """Increment user's score and synchronize with statistics"""
        user_id = str(user_id)
        if user_id not in self.stats:
            self._init_user_stats(user_id)

        # Initialize score if needed
        if user_id not in self.scores:
            self.scores[user_id] = 0

        # Increment score and synchronize with stats
        self.scores[user_id] += 1
        stats = self.stats[user_id]
        stats['correct_answers'] = self.scores[user_id]
        stats['total_quizzes'] = max(stats['total_quizzes'] + 1, stats['correct_answers'])

        # Record the attempt after synchronizing
        self.record_attempt(user_id, True)
        self.save_data()

    def get_score(self, user_id: int) -> int:
        return self.scores.get(str(user_id), 0)

    def add_active_chat(self, chat_id: int):
        """Add a chat to active chats with proper initialization"""
        try:
            if chat_id not in self.active_chats:
                self.active_chats.append(chat_id)
                # Initialize tracking structures for new chat
                chat_id_str = str(chat_id)
                self.recent_questions[chat_id_str] = deque(maxlen=50)
                self.last_question_time[chat_id_str] = {}
                self._initialize_available_questions(chat_id)
                # Save changes immediately
                self.save_data(force=True)
                logger.info(f"Added chat {chat_id} to active chats with initialization")
        except Exception as e:
            logger.error(f"Error adding chat {chat_id}: {e}")

    def remove_active_chat(self, chat_id: int):
        """Remove a chat from active chats with cleanup"""
        try:
            chat_id_str = str(chat_id)
            if chat_id in self.active_chats:
                self.active_chats.remove(chat_id)

                # Cleanup chat data
                if chat_id_str in self.last_question_time:
                    del self.last_question_time[chat_id_str]
                if chat_id_str in self.recent_questions:
                    del self.recent_questions[chat_id_str]
                if chat_id_str in self.available_questions:
                    del self.available_questions[chat_id_str]

                # Save changes immediately
                self.save_data(force=True)
                logger.info(f"Removed chat {chat_id} from active chats with cleanup")
        except Exception as e:
            logger.error(f"Error removing chat {chat_id}: {e}")

    def get_active_chats(self) -> List[int]:
        return self.active_chats

    def cleanup_oldquestions(self) -> None:
        """Clean up old questions history and inactive chats"""
        try:
            current_date= datetime.now().strftime('%Y-%m-%d')
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            # Clean up old questions from inactive chats
            inactive_chats = []
            for chat_id in self.active_chats:
                chat_id_str = str(chat_id)
                last_activity = self.get_group_last_activity(chat_id_str)

                if not last_activity or last_activity < week_ago:
                    inactive_chats.append(chat_id)

                    # Clean up associated data
                    if chat_id_str in self.recent_questions:
                        del self.recent_questions[chat_id_str]
                    if chat_id_str in self.last_question_time:
                        del self.last_question_time[chat_id_str]
                    if chat_id_str in self.available_questions:
                        del self.available_questions[chat_id_str]

            # Remove inactive chats
            for chat_id in inactive_chats:
                if chat_id in self.active_chats:
                    self.active_chats.remove(chat_id)
                    logger.info(f"Removed inactive chat: {chat_id}")

            # Save changes
            if inactive_chats:
                self.save_data(force=True)
                logger.info(f"Cleaned up {len(inactive_chats)} inactive chats")

            # Clean up old daily activity data
            for user_id, stats in self.stats.items():
                try:
                    # Clean daily activity
                    old_dates = [
                        date for date in stats['daily_activity']
                        if date < week_ago
                    ]
                    for date in old_dates:
                        del stats['daily_activity'][date]

                    # Clean group activity
                    for group_id, group_stats in stats.get('groups', {}).items():
                        old_group_dates = [
                            date for date in group_stats.get('daily_activity', {})
                            if date < week_ago
                        ]
                        for date in old_group_dates:
                            del group_stats['daily_activity'][date]

                except Exception as e:
                    logger.error(f"Error cleaning up stats for user {user_id}: {e}")
                    continue

            logger.info("Completed cleanup of old questions and inactive chats")

        except Exception as e:
            logger.error(f"Error in cleanup_old_questions: {e}")

    def validate_question(self, question: Dict) -> bool:
        """Validate if a question's format and answer are correct"""
        try:
            # Basic structure validation
            if not all(key in question for key in ['question', 'options', 'correct_answer']):
                return False

            # Validate options array
            if not isinstance(question['options'], list) or len(question['options']) != 4:
                return False

            # Validate correct_answer is within bounds
            if not isinstance(question['correct_answer'], int) or not (0 <= question['correct_answer'] < 4):
                return False

            return True
        except Exception:
            return False

    def remove_invalidquestions(self):
        """Remove questions with invalid format or answers"""
        try:
            initial_count = len(self.questions)
            self.questions = [q for q in self.questions if self.validate_question(q)]
            removed_count = initial_count - len(self.questions)

            # Save changes immediately
            self.save_data(force=True)

            logger.info(f"Removed {removed_count} invalid questions. Remaining: {len(self.questions)}")
            return {
                'initial_count': initial_count,
                'removed_count': removed_count,
                'remaining_count': len(self.questions)
            }
        except Exception as e:
            logger.error(f"Error removing invalid questions: {e}")
            raise

    def clear_all_questions(self) -> bool:
        """Clear all questions from the database"""
        try:
            self.questions = []
            self.save_data(force=True)
            logger.info("All questions cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing questions: {e}")
            return False

    def reload_data(self):
        """Reload all data while preserving state"""
        try:
            logger.info("Starting full data reload...")

            # Store current state
            current_stats = self.stats.copy()
            current_scores = self.scores.copy()
            current_active_chats = self.active_chats.copy()

            # Reset caches and tracking structures
            self._cached_questions = None
            self._cached_leaderboard = None
            self._leaderboard_cache_time = None
            self.recent_questions.clear()
            self.last_question_time.clear()
            self.available_questions.clear()

            # Reload all data files
            self.load_data()

            # Merge states
            self.stats.update(current_stats)
            self.scores.update(current_scores)

            # Collect all active chats from both direct tracking and user stats
            all_active_chats = set(current_active_chats)

            # Add chats from group activity in user stats
            for user_stats in self.stats.values():
                # Add all group chats from user stats
                all_active_chats.update(
                    int(chat_id) for chat_id in user_stats.get('groups', {}).keys()
                )
                # Add private chats (where user_id matches chat_id)
                if user_stats.get('last_quiz_date'):
                    all_active_chats.add(int(list(user_stats.keys())[0]))

            # Update active_chats with merged unique chats
            self.active_chats = sorted(all_active_chats)

            # Force save to ensure clean state
            self.save_data(force=True)

            # Log detailed results
            logger.info("Data reload completed successfully:")
            logger.info(f"- Active chats: {len(self.active_chats)}")
            logger.info(f"- Active users: {len(self.stats)}")
            logger.info(f"- Total scores: {len(self.scores)}")
            logger.info(f"- Questions loaded: {len(self.questions)}")
            return True

        except Exception as e:
            logger.error(f"Error reloading data: {str(e)}\n{traceback.format_exc()}")
            raise

    def get_group_last_activity(self, chat_id: str) -> Optional[str]:
        """Get the last activity date for a group"""
        try:
            latest_activity = None
            chat_id_str = str(chat_id)

            # Check all users' group activity
            for stats in self.stats.values():
                if chat_id_str in stats.get('groups', {}):
                    group_last_activity = stats['groups'][chat_id_str].get('last_activity_date')
                    if group_last_activity:
                        if not latest_activity or group_last_activity > latest_activity:
                            latest_activity = group_last_activity

            return latest_activity
        except Exception as e:
            logger.error(f"Error getting group last activity: {e}")
            return None

    def get_global_statistics(self) -> Dict:
        """Get comprehensive global statistics with accurate user counting"""
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            # Initialize stats structure
            stats = {
                'users': {
                    'total': 0,
                    'active_today': 0,
                    'active_week': 0,
                    'private_chat': 0,
                    'group_users': 0
                },
                'groups': {
                    'total': len(self.active_chats),
                    'active_today': 0,
                    'active_week': 0
                },
                'quizzes': {
                    'total_attempts': 0,
                    'correct_answers': 0,
                    'today_attempts': 0,
                    'week_attempts': 0
                },
                'performance': {
                    'success_rate': 0,
                    'questions_available': len(self.questions)
                }
            }

            # Get all group members
            group_users = set()
            private_users = set()
            for chat_id in self.active_chats:
                members = self.get_group_members(str(chat_id))
                group_users.update(members)

            # Process user statistics
            for user_id, user_stats in self.stats.items():
                # Track private chat users
                if 'private_chat_activity' in user_stats and user_stats['private_chat_activity'].get('total_messages', 0) > 0:
                    private_users.add(user_id)
                    stats['users']['private_chat'] += 1

                # Track activity periods
                last_active = user_stats.get('last_activity_date')
                if last_active:
                    if last_active == current_date:
                        stats['users']['active_today'] += 1
                    if last_active >= week_start:
                        stats['users']['active_week'] += 1

                # Track quiz performance
                stats['quizzes']['total_attempts'] += user_stats.get('total_quizzes', 0)
                stats['quizzes']['correct_answers'] += user_stats.get('correct_answers', 0)

                # Track today's attempts
                today_activity = user_stats.get('daily_activity', {}).get(current_date, {})
                stats['quizzes']['today_attempts'] += today_activity.get('attempts', 0)

                # Track week's attempts
                stats['quizzes']['week_attempts'] += sum(
                    day_stats.get('attempts', 0)
                    for date, day_stats in user_stats.get('daily_activity', {}).items()
                    if date >= week_start
                )

            # Update group activity
            for chat_id in self.active_chats:
                chat_id_str = str(chat_id)
                last_activity = self.get_group_last_activity(chat_id_str)
                if last_activity:
                    if last_activity == current_date:
                        stats['groups']['active_today'] += 1
                    if last_activity >= week_start:
                        stats['groups']['active_week'] += 1

            # Calculate final user counts
            all_users = group_users.union(private_users)
            stats['users']['total'] = len(all_users)
            stats['users']['group_users'] = len(group_users)

            # Calculate success rate
            if stats['quizzes']['total_attempts'] > 0:
                stats['performance']['success_rate'] = round(
                    (stats['quizzes']['correct_answers'] / stats['quizzes']['total_attempts']) * 100, 1
                )

            logger.info(f"Global stats generated: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting global statistics: {e}\n{traceback.format_exc()}")
            return {
                'users': {'total': 0, 'active_today': 0, 'active_week': 0, 'private_chat': 0, 'group_users': 0},
                'groups': {'total': 0, 'active_today': 0, 'active_week': 0},
                'quizzes': {'total_attempts': 0, 'correct_answers': 0, 'today_attempts': 0, 'week_attempts': 0},
                'performance': {'success_rate': 0, 'questions_available': 0}
            }

    def get_group_members(self, chat_id: str) -> set:
        """Get all members who have participated in a group"""
        members = set()
        for user_id, stats in self.stats.items():
            if 'groups' in stats and chat_id in stats['groups']:
                members.add(user_id)
        return members

    def track_user_activity(self, user_id: int, chat_id: int) -> None:
        """Track user activity in real-time"""
        try:
            user_id_str = str(user_id)
            chat_id_str = str(chat_id)
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Initialize user if not exists
            if user_id_str not in self.stats:
                self._init_user_stats(user_id_str)

            # Update user's last activity
            self.stats[user_id_str]['last_activity_date'] = current_date

            # Update group activity if it's a group chat
            if chat_id_str not in self.stats[user_id_str].get('groups', {}):
                self.stats[user_id_str]['groups'][chat_id_str] = {
                    'total_quizzes': 0,
                    'correct_answers': 0,
                    'score': 0,
                    'last_activity_date': current_date,
                    'daily_activity': {},
                    'current_streak': 0,
                    'longest_streak': 0,
                    'last_correct_date': None
                }

            # Force save to ensure no data loss
            self.save_data(force=True)
            logger.info(f"Tracked activity for user {user_id} in chat {chat_id}")

        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")

    def get_active_users(self) -> List[str]:
        """Get list of active users with improved tracking"""
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            active_users = set()

            # Check all activity types
            for user_id, stats in self.stats.items():
                # Check last activity date
                last_activity = stats.get('last_activity_date')
                if last_activity and last_activity >= week_start:
                    active_users.add(user_id)
                    continue

                # Check private chat activity
                private_chat = stats.get('private_chat_activity', {})
                if private_chat.get('last_active', '') >= week_start:
                    active_users.add(user_id)
                    continue

                # Check group activity
                for group_stats in stats.get('groups', {}).values():
                    if group_stats.get('last_activity_date', '') >= week_start:
                        active_users.add(user_id)
                        break

            return list(active_users)
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    def update_all_stats(self) -> None:
        """Update all statistics in real-time with enhanced tracking"""
        try:
            current_date = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            # Update user stats
            for user_id, stats in self.stats.items():
                try:
                    # Ensure required fields exist
                    if 'join_date' not in stats:
                        stats['join_date'] = current_date
                    if 'last_activity_date' not in stats:
                        stats['last_activity_date'] = current_date
                    if 'private_chat_activity' not in stats:
                        stats['private_chat_activity'] = {
                            'total_messages': 0,
                            'last_active': current_date
                        }

                    # Ensure daily activity exists
                    if current_date not in stats['daily_activity']:
                        stats['daily_activity'][current_date] = {
                            'attempts': 0,
                            'correct': 0
                        }

                    # Update group stats
                    for group_id, group_stats in stats.get('groups', {}).items():
                        if current_date not in group_stats.get('daily_activity', {}):
                            group_stats['daily_activity'][current_date] = {
                                'attempts': 0,
                                'correct': 0
                            }

                        # Clean up old daily activity data
                        old_dates = [
                            date for date in group_stats['daily_activity']
                            if date < week_start
                        ]
                        for date in old_dates:
                            del group_stats['daily_activity'][date]

                    # Sync with scores
                    score = self.scores.get(user_id, 0)
                    if score != stats['correct_answers']:
                        stats['correct_answers'] = score
                        stats['total_quizzes'] = max(stats['total_quizzes'], score)

                except Exception as e:
                    logger.error(f"Error updating stats for user {user_id}: {e}")
                    continue

            # Force save after updates
            self.save_data(force=True)
            logger.info("All stats updated successfully")

        except Exception as e:
            logger.error(f"Error updating all stats: {e}")

    def cleanup_old_questions(self):
        """Cleanup old question history periodically"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=24)

            for chat_id in list(self.recent_questions.keys()):
                # Clear tracking for inactive chats
                if not self.recent_questions[chat_id]:
                    del self.recent_questions[chat_id]
                    if chat_id in self.last_question_time:
                        del self.last_question_time[chat_id]
                    if chat_id in self.available_questions:
                        del self.available_questions[chat_id]
                    continue

                # Remove old question timestamps
                if chat_id in self.last_question_time:
                    old_questions = [
                        q for q, t in self.last_question_time[chat_id].items()
                        if t < cutoff_time
                    ]
                    for q in old_questions:
                        del self.last_question_time[chat_id][q]

            logger.info("Completed cleanup of old questions history")
        except Exception as e:
            logger.error(f"Error in cleanup_old_questions: {e}")