"""
Database Manager for Telegram Quiz Bot
Handles all SQLite database operations for quizzes, users, developers, groups, and statistics
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations for the quiz bot"""
    
    def __init__(self, db_path: str = None):
        """Initialize database manager"""
        self.db_path = db_path or config.DATABASE_PATH
        self.init_database()
        logger.info(f"Database initialized at {self.db_path}")
        
        # Run timestamp migration to fix ISO format timestamps
        try:
            migration_result = self.migrate_iso_timestamps_to_space_format()
            if migration_result['activity_logs'] > 0 or migration_result['performance_metrics'] > 0:
                logger.info(f"Migrated timestamps: activity_logs={migration_result['activity_logs']}, performance_metrics={migration_result['performance_metrics']}")
        except Exception as e:
            logger.error(f"Timestamp migration failed (non-critical): {e}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: Add category column if it doesn't exist
            cursor.execute("PRAGMA table_info(questions)")
            question_columns = [column[1] for column in cursor.fetchall()]
            if 'category' not in question_columns:
                cursor.execute('ALTER TABLE questions ADD COLUMN category TEXT')
                logger.info("Added category column to questions table")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    current_score INTEGER DEFAULT 0,
                    total_quizzes INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    wrong_answers INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    last_activity_date TEXT,
                    has_pm_access INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migration: Add has_pm_access column if it doesn't exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'has_pm_access' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN has_pm_access INTEGER DEFAULT 0')
                logger.info("Added has_pm_access column to users table")
            
            # Migration: Add last_quiz_message_id column if it doesn't exist
            if 'last_quiz_message_id' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN last_quiz_message_id INTEGER')
                logger.info("Added last_quiz_message_id column to users table")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS developers (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    chat_type TEXT,
                    is_active INTEGER DEFAULT 1,
                    last_activity_date TEXT,
                    total_quizzes_sent INTEGER DEFAULT 0,
                    last_quiz_message_id INTEGER,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute("PRAGMA table_info(groups)")
            group_columns = [column[1] for column in cursor.fetchall()]
            if 'last_quiz_message_id' not in group_columns:
                cursor.execute('ALTER TABLE groups ADD COLUMN last_quiz_message_id INTEGER')
                logger.info("Added last_quiz_message_id column to groups table")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_daily_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_date TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    correct INTEGER DEFAULT 0,
                    wrong INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, activity_date)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER,
                    question_id INTEGER,
                    question_text TEXT,
                    user_answer INTEGER,
                    correct_answer INTEGER,
                    is_correct INTEGER,
                    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (question_id) REFERENCES questions (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id TEXT UNIQUE NOT NULL,
                    sender_id INTEGER NOT NULL,
                    message_data TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    quizzes_sent_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    message_text TEXT,
                    total_targets INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    skipped_count INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_activity_date 
                ON user_daily_activity(user_id, activity_date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_quiz_history_user 
                ON quiz_history(user_id, answered_at)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    user_id INTEGER,
                    chat_id INTEGER,
                    username TEXT,
                    chat_title TEXT,
                    command TEXT,
                    details TEXT,
                    success INTEGER DEFAULT 1,
                    response_time_ms INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp 
                ON activity_logs(timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_logs_type 
                ON activity_logs(activity_type, timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_logs_user 
                ON activity_logs(user_id, timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_logs_chat 
                ON activity_logs(chat_id, timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT,
                    value REAL NOT NULL,
                    unit TEXT,
                    details TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp 
                ON performance_metrics(timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_type 
                ON performance_metrics(metric_type, timestamp DESC)
            ''')
            
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_activity_logs_type_time 
                ON activity_logs(activity_type, timestamp)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_activity_logs_command 
                ON activity_logs(command)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_activity_logs_user_time 
                ON activity_logs(user_id, timestamp)''')
            
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_performance_metrics_type_time 
                ON performance_metrics(metric_type, timestamp)''')
            
            # Additional performance-critical indexes
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_quiz_stats_date 
                ON quiz_stats(date)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_broadcast_logs_admin 
                ON broadcast_logs(admin_id, timestamp DESC)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_broadcast_logs_timestamp 
                ON broadcast_logs(timestamp DESC)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_users_activity 
                ON users(last_activity_date, total_quizzes)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_groups_activity 
                ON groups(is_active, last_activity_date)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_quiz_history_chat 
                ON quiz_history(chat_id, answered_at DESC)''')
            
            logger.info("Database schema initialized successfully with optimized indexes")
    
    def add_question(self, question: str, options: List[str], correct_answer: int) -> int:
        """Add a new quiz question"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            options_json = json.dumps(options)
            cursor.execute('''
                INSERT INTO questions (question, options, correct_answer)
                VALUES (?, ?, ?)
            ''', (question, options_json, correct_answer))
            return cursor.lastrowid
    
    def get_all_questions(self) -> List[Dict]:
        """Get all quiz questions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM questions ORDER BY id')
            rows = cursor.fetchall()
            return [
                {
                    'id': row['id'],
                    'question': row['question'],
                    'options': json.loads(row['options']),
                    'correct_answer': row['correct_answer']
                }
                for row in rows
            ]
    
    def get_questions_by_category(self, category: str) -> List[Dict]:
        """Get quiz questions filtered by category"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM questions WHERE category = ? ORDER BY id', (category,))
            rows = cursor.fetchall()
            return [
                {
                    'id': row['id'],
                    'question': row['question'],
                    'options': row['options'],
                    'correct_answer': row['correct_answer'],
                    'category': row['category'] if 'category' in row.keys() else None
                }
                for row in rows
            ]
    
    def delete_question(self, question_id: int) -> bool:
        """Delete a quiz question"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
            return cursor.rowcount > 0
    
    def update_question(self, question_id: int, question: str, options: List[str], correct_answer: int) -> bool:
        """Update a quiz question"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            options_json = json.dumps(options)
            cursor.execute('''
                UPDATE questions 
                SET question = ?, options = ?, correct_answer = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (question, options_json, correct_answer, question_id))
            return cursor.rowcount > 0
    
    def add_or_update_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, last_name))
    
    def update_user_score(self, user_id: int, is_correct: bool, activity_date: str = None):
        """Update user score and statistics"""
        if not activity_date:
            activity_date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if is_correct:
                cursor.execute('''
                    UPDATE users 
                    SET current_score = current_score + 1,
                        total_quizzes = total_quizzes + 1,
                        correct_answers = correct_answers + 1,
                        last_activity_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (activity_date, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET current_score = CASE WHEN current_score > 0 THEN current_score - 1 ELSE 0 END,
                        total_quizzes = total_quizzes + 1,
                        wrong_answers = wrong_answers + 1,
                        last_activity_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (activity_date, user_id))
            
            cursor.execute('''
                UPDATE users 
                SET success_rate = CASE 
                    WHEN total_quizzes > 0 THEN (correct_answers * 100.0 / total_quizzes)
                    ELSE 0.0 
                END
                WHERE user_id = ?
            ''', (user_id,))
            
            cursor.execute('''
                INSERT INTO user_daily_activity (user_id, activity_date, attempts, correct, wrong)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(user_id, activity_date) DO UPDATE SET
                    attempts = attempts + 1,
                    correct = correct + ?,
                    wrong = wrong + ?
            ''', (user_id, activity_date, 1 if is_correct else 0, 0 if is_correct else 1,
                  1 if is_correct else 0, 0 if is_correct else 1))
    
    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_all_users_stats(self) -> List[Dict]:
        """Get all users statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY current_score DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_users(self) -> List[Dict]:
        """Get only active users who have taken at least one quiz (can receive broadcasts)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE total_quizzes > 0 ORDER BY current_score DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pm_accessible_users(self) -> List[Dict]:
        """Get only users who have started a PM conversation with the bot"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE has_pm_access = 1 ORDER BY current_score DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def set_user_pm_access(self, user_id: int, has_access: bool = True):
        """Mark that a user has started a PM conversation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET has_pm_access = ?
                WHERE user_id = ?
            ''', (1 if has_access else 0, user_id))
    
    def add_developer(self, user_id: int, username: str = None, first_name: str = None, 
                     last_name: str = None, added_by: int = None):
        """Add a developer"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO developers (user_id, username, first_name, last_name, added_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, added_by))
    
    def remove_developer(self, user_id: int) -> bool:
        """Remove a developer"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM developers WHERE user_id = ?', (user_id,))
            return cursor.rowcount > 0
    
    def get_all_developers(self) -> List[Dict]:
        """Get all developers"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM developers ORDER BY added_at')
            return [dict(row) for row in cursor.fetchall()]
    
    def is_developer(self, user_id: int) -> bool:
        """Check if user is a developer"""
        if user_id in config.AUTHORIZED_USERS:
            return True
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM developers WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
    
    def add_or_update_group(self, chat_id: int, chat_title: str = None, chat_type: str = None):
        """Add or update group information"""
        activity_date = datetime.now().strftime('%Y-%m-%d')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO groups (chat_id, chat_title, chat_type, last_activity_date)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_title = excluded.chat_title,
                    chat_type = excluded.chat_type,
                    last_activity_date = excluded.last_activity_date,
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
            ''', (chat_id, chat_title, chat_type, activity_date))
    
    def get_all_groups(self, active_only: bool = True) -> List[Dict]:
        """Get all groups"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT * FROM groups WHERE is_active = 1 ORDER BY last_activity_date DESC')
            else:
                cursor.execute('SELECT * FROM groups ORDER BY last_activity_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def increment_group_quiz_count(self, chat_id: int):
        """Increment quiz count for a group"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE groups 
                SET total_quizzes_sent = total_quizzes_sent + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            ''', (chat_id,))
    
    def record_quiz_answer(self, user_id: int, chat_id: int, question_id: int, 
                          question_text: str, user_answer: int, correct_answer: int):
        """Record a quiz answer in history"""
        is_correct = 1 if user_answer == correct_answer else 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quiz_history (user_id, chat_id, question_id, question_text, 
                                        user_answer, correct_answer, is_correct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, question_id, question_text, user_answer, correct_answer, is_correct))
    
    def get_stats_summary(self) -> Dict:
        """Get comprehensive statistics summary - OPTIMIZED: reduced 11 queries to 3 queries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - 
                         __import__('datetime').timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
            month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            # Query 1: Get all counts in one query
            cursor.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM questions) as total_questions,
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM groups WHERE is_active = 1) as total_groups,
                    (SELECT SUM(total_quizzes) FROM users) as quizzes_alltime,
                    (SELECT SUM(correct_answers) FROM users) as correct_alltime
            ''')
            counts = cursor.fetchone()
            
            # Query 2: Get activity data in one query with aggregation
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN activity_date = ? THEN attempts ELSE 0 END) as quizzes_today,
                    SUM(CASE WHEN activity_date >= ? THEN attempts ELSE 0 END) as quizzes_week,
                    SUM(CASE WHEN activity_date >= ? THEN attempts ELSE 0 END) as quizzes_month,
                    COUNT(DISTINCT CASE WHEN activity_date = ? THEN user_id END) as active_users_today,
                    COUNT(DISTINCT CASE WHEN activity_date >= ? THEN user_id END) as active_users_week
                FROM user_daily_activity
            ''', (today, week_start, month_start, today, week_start))
            activity = cursor.fetchone()
            
            quizzes_alltime = counts['quizzes_alltime'] or 0
            correct_alltime = counts['correct_alltime'] or 0
            
            return {
                'total_questions': counts['total_questions'],
                'total_users': counts['total_users'],
                'total_groups': counts['total_groups'],
                'quizzes_today': activity['quizzes_today'] or 0,
                'quizzes_week': activity['quizzes_week'] or 0,
                'quizzes_month': activity['quizzes_month'] or 0,
                'quizzes_alltime': quizzes_alltime,
                'correct_alltime': correct_alltime,
                'success_rate': round((correct_alltime / max(quizzes_alltime, 1) * 100), 1),
                'active_users_today': activity['active_users_today'] or 0,
                'active_users_week': activity['active_users_week'] or 0,
                'today_date': today,
                'week_start': week_start,
                'month_start': month_start
            }
    
    def migrate_from_json(self, questions_file: str, users_file: str, developers_file: str, 
                         chats_file: str):
        """Migrate data from JSON files to SQLite database"""
        import os
        
        try:
            if os.path.exists(questions_file):
                with open(questions_file, 'r') as f:
                    questions = json.load(f)
                    for q in questions:
                        self.add_question(q['question'], q['options'], q['correct_answer'])
                logger.info(f"Migrated {len(questions)} questions from JSON")
            
            if os.path.exists(users_file):
                with open(users_file, 'r') as f:
                    users = json.load(f)
                    for user_id, stats in users.items():
                        if isinstance(stats, dict) and 'total_quizzes' in stats:
                            with self.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT OR REPLACE INTO users 
                                    (user_id, current_score, total_quizzes, correct_answers, 
                                     wrong_answers, success_rate, last_activity_date)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    int(user_id),
                                    stats.get('current_score', 0),
                                    stats.get('total_quizzes', 0),
                                    stats.get('correct_answers', 0),
                                    stats.get('wrong_answers', 0),
                                    stats.get('success_rate', 0.0),
                                    stats.get('last_activity_date')
                                ))
                logger.info(f"Migrated {len(users)} users from JSON")
            
            if os.path.exists(developers_file):
                with open(developers_file, 'r') as f:
                    dev_data = json.load(f)
                    developers = dev_data.get('developers', []) if isinstance(dev_data, dict) else dev_data
                    for dev_id in developers:
                        if isinstance(dev_id, int) or (isinstance(dev_id, str) and dev_id.isdigit()):
                            self.add_developer(int(dev_id))
                logger.info(f"Migrated {len(developers)} developers from JSON")
            
            if os.path.exists(chats_file):
                with open(chats_file, 'r') as f:
                    chats = json.load(f)
                    for chat_id in chats:
                        self.add_or_update_group(int(chat_id))
                logger.info(f"Migrated {len(chats)} groups from JSON")
            
            logger.info("JSON to SQLite migration completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error migrating from JSON: {e}")
            return False
    
    def save_broadcast(self, broadcast_id: str, sender_id: int, message_data: dict) -> bool:
        """Save broadcast data to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO broadcasts (broadcast_id, sender_id, message_data)
                    VALUES (?, ?, ?)
                ''', (broadcast_id, sender_id, json.dumps(message_data)))
                return True
        except Exception as e:
            logger.error(f"Error saving broadcast: {e}")
            return False
    
    def get_latest_broadcast(self) -> Optional[Dict]:
        """Get the most recent broadcast"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT broadcast_id, sender_id, message_data, sent_at
                    FROM broadcasts
                    ORDER BY sent_at DESC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    return {
                        'broadcast_id': row['broadcast_id'],
                        'sender_id': row['sender_id'],
                        'message_data': json.loads(row['message_data']),
                        'sent_at': row['sent_at']
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting latest broadcast: {e}")
            return None
    
    def delete_broadcast(self, broadcast_id: str) -> bool:
        """Delete broadcast from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM broadcasts WHERE broadcast_id = ?', (broadcast_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting broadcast: {e}")
            return False
    
    def remove_inactive_user(self, user_id: int) -> bool:
        """Remove inactive user from database (blocked bot or deactivated)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Removed inactive user {user_id} from database")
                return success
        except Exception as e:
            logger.error(f"Error removing inactive user {user_id}: {e}")
            return False
    
    def remove_inactive_group(self, chat_id: int) -> bool:
        """Remove inactive group from database (bot was kicked or not a member)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM groups WHERE chat_id = ?', (chat_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Removed inactive group {chat_id} from database")
                return success
        except Exception as e:
            logger.error(f"Error removing inactive group {chat_id}: {e}")
            return False
    
    def update_last_quiz_message(self, chat_id: int, message_id: int):
        """Store last quiz message ID for a chat (user or group)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if chat_id > 0:
                    cursor.execute('''
                        UPDATE users 
                        SET last_quiz_message_id = ?
                        WHERE user_id = ?
                    ''', (message_id, chat_id))
                else:
                    cursor.execute('''
                        UPDATE groups 
                        SET last_quiz_message_id = ?
                        WHERE chat_id = ?
                    ''', (message_id, chat_id))
                
                logger.debug(f"Updated last quiz message ID for chat {chat_id}: {message_id}")
        except Exception as e:
            logger.error(f"Error updating last quiz message for chat {chat_id}: {e}")
    
    def get_last_quiz_message(self, chat_id: int) -> Optional[int]:
        """Get last quiz message ID for a chat (user or group)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if chat_id > 0:
                    cursor.execute('SELECT last_quiz_message_id FROM users WHERE user_id = ?', (chat_id,))
                else:
                    cursor.execute('SELECT last_quiz_message_id FROM groups WHERE chat_id = ?', (chat_id,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
                return None
        except Exception as e:
            logger.error(f"Error getting last quiz message for chat {chat_id}: {e}")
            return None
    
    def increment_quiz_count(self, date: str = None):
        """Increment quiz count for specific date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO quiz_stats (date, quizzes_sent_count)
                    VALUES (?, 1)
                    ON CONFLICT(date) DO UPDATE SET
                        quizzes_sent_count = quizzes_sent_count + 1
                ''', (date,))
                logger.debug(f"Incremented quiz count for date {date}")
        except Exception as e:
            logger.error(f"Error incrementing quiz count for date {date}: {e}")
    
    def get_quiz_stats_today(self) -> int:
        """Get today's quiz count"""
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT quizzes_sent_count FROM quiz_stats WHERE date = ?', (today,))
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting today's quiz stats: {e}")
            return 0
    
    def get_quiz_stats_week(self) -> int:
        """Get this week's quiz count"""
        from datetime import timedelta
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(quizzes_sent_count) 
                    FROM quiz_stats 
                    WHERE date >= ?
                ''', (week_start,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error(f"Error getting week's quiz stats: {e}")
            return 0
    
    def get_quiz_stats_month(self) -> int:
        """Get this month's quiz count"""
        month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(quizzes_sent_count) 
                    FROM quiz_stats 
                    WHERE date >= ?
                ''', (month_start,))
                row = cursor.fetchone()
                return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error(f"Error getting month's quiz stats: {e}")
            return 0
    
    def get_quiz_stats_alltime(self) -> int:
        """Get all-time quiz count"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT SUM(quizzes_sent_count) FROM quiz_stats')
                row = cursor.fetchone()
                return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error(f"Error getting all-time quiz stats: {e}")
            return 0
    
    def get_total_quizzes_sent(self) -> int:
        """Sum all quiz counts (alias for get_quiz_stats_alltime)"""
        return self.get_quiz_stats_alltime()
    
    def log_broadcast(self, admin_id: int, message_text: str, total_targets: int, 
                     sent_count: int, failed_count: int, skipped_count: int):
        """Log broadcast to database for historical tracking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO broadcast_logs 
                    (admin_id, message_text, total_targets, sent_count, failed_count, skipped_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (admin_id, message_text, total_targets, sent_count, failed_count, skipped_count))
                logger.info(f"Logged broadcast by admin {admin_id}: {sent_count}/{total_targets} sent")
        except Exception as e:
            logger.error(f"Error logging broadcast: {e}")
    
    def log_activity(self, activity_type: str, user_id: int = None, chat_id: int = None, 
                    username: str = None, chat_title: str = None, command: str = None, 
                    details: dict = None, success: bool = True, response_time_ms: int = None):
        """
        Log activity to the activity_logs table immediately
        
        Args:
            activity_type: Type of activity ('command', 'quiz_sent', 'quiz_answer', 'broadcast', 
                          'user_join', 'group_join', 'error', 'api_call')
            user_id: User ID (optional)
            chat_id: Chat ID (optional)
            username: Username (optional)
            chat_title: Chat title (optional)
            command: Command name for command activities (optional)
            details: Dictionary with extra data, will be converted to JSON (optional)
            success: Whether the activity was successful (default: True)
            response_time_ms: Response time in milliseconds (optional)
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            details_json = json.dumps(details) if details else None
            success_int = 1 if success else 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_logs 
                    (timestamp, activity_type, user_id, chat_id, username, chat_title, 
                     command, details, success, response_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, activity_type, user_id, chat_id, username, chat_title, 
                      command, details_json, success_int, response_time_ms))
                
                logger.debug(f"Logged activity: {activity_type} - User: {user_id}, Chat: {chat_id}, Success: {success}")
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
    
    def get_recent_activities(self, limit: int = 100, activity_type: str = None) -> List[Dict]:
        """
        Get recent activities with optional filtering by type
        
        Args:
            limit: Maximum number of activities to return (default: 100)
            activity_type: Filter by specific activity type (optional)
            
        Returns:
            List of activity dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if activity_type:
                    cursor.execute('''
                        SELECT * FROM activity_logs 
                        WHERE activity_type = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (activity_type, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM activity_logs 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                activities = []
                for row in rows:
                    activity = dict(row)
                    if activity.get('details'):
                        try:
                            activity['details'] = json.loads(activity['details'])
                        except json.JSONDecodeError:
                            pass
                    activities.append(activity)
                
                logger.debug(f"Retrieved {len(activities)} recent activities")
                return activities
        except Exception as e:
            logger.error(f"Error getting recent activities: {e}")
            return []
    
    def get_activities_by_user(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get activity history for a specific user
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of activities to return (default: 50)
            
        Returns:
            List of activity dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM activity_logs 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                rows = cursor.fetchall()
                activities = []
                for row in rows:
                    activity = dict(row)
                    if activity.get('details'):
                        try:
                            activity['details'] = json.loads(activity['details'])
                        except json.JSONDecodeError:
                            pass
                    activities.append(activity)
                
                logger.debug(f"Retrieved {len(activities)} activities for user {user_id}")
                return activities
        except Exception as e:
            logger.error(f"Error getting activities for user {user_id}: {e}")
            return []
    
    def get_activities_by_chat(self, chat_id: int, limit: int = 50) -> List[Dict]:
        """
        Get activity history for a specific chat
        
        Args:
            chat_id: Chat ID to filter by
            limit: Maximum number of activities to return (default: 50)
            
        Returns:
            List of activity dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM activity_logs 
                    WHERE chat_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (chat_id, limit))
                
                rows = cursor.fetchall()
                activities = []
                for row in rows:
                    activity = dict(row)
                    if activity.get('details'):
                        try:
                            activity['details'] = json.loads(activity['details'])
                        except json.JSONDecodeError:
                            pass
                    activities.append(activity)
                
                logger.debug(f"Retrieved {len(activities)} activities for chat {chat_id}")
                return activities
        except Exception as e:
            logger.error(f"Error getting activities for chat {chat_id}: {e}")
            return []
    
    def get_activities_today(self) -> int:
        """
        Get count of today's activities
        
        Returns:
            Count of activities for today
        """
        try:
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM activity_logs 
                    WHERE timestamp >= ? AND timestamp <= ?
                ''', (today_start, today_end))
                
                row = cursor.fetchone()
                count = row['count'] if row else 0
                logger.debug(f"Activities today: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting today's activities count: {e}")
            return 0
    
    def get_activity_stats(self, days: int = 7) -> Dict:
        """
        Get aggregated activity statistics for the last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with activity statistics including:
            - total_activities: Total count
            - activities_by_type: Count by activity type
            - activities_by_day: Count by date
            - success_rate: Percentage of successful activities
            - avg_response_time_ms: Average response time
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) as total 
                    FROM activity_logs 
                    WHERE timestamp >= ?
                ''', (start_timestamp,))
                total_activities = cursor.fetchone()['total']
                
                cursor.execute('''
                    SELECT activity_type, COUNT(*) as count 
                    FROM activity_logs 
                    WHERE timestamp >= ?
                    GROUP BY activity_type
                    ORDER BY count DESC
                ''', (start_timestamp,))
                activities_by_type = {row['activity_type']: row['count'] for row in cursor.fetchall()}
                
                cursor.execute('''
                    SELECT strftime('%Y-%m-%d', timestamp) as date, COUNT(*) as count 
                    FROM activity_logs 
                    WHERE timestamp >= ?
                    GROUP BY strftime('%Y-%m-%d', timestamp)
                    ORDER BY date DESC
                ''', (start_timestamp,))
                activities_by_day = {row['date']: row['count'] for row in cursor.fetchall()}
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                    FROM activity_logs 
                    WHERE timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                total = row['total']
                successful = row['successful']
                success_rate = round((successful / max(total, 1)) * 100, 2)
                
                cursor.execute('''
                    SELECT AVG(response_time_ms) as avg_time 
                    FROM activity_logs 
                    WHERE timestamp >= ? AND response_time_ms IS NOT NULL
                ''', (start_timestamp,))
                row = cursor.fetchone()
                avg_response_time = round(row['avg_time'], 2) if row['avg_time'] else 0
                
                stats = {
                    'total_activities': total_activities,
                    'activities_by_type': activities_by_type,
                    'activities_by_day': activities_by_day,
                    'success_rate': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'period_days': days,
                    'start_date': start_timestamp
                }
                
                logger.debug(f"Retrieved activity stats for last {days} days: {total_activities} activities")
                return stats
        except Exception as e:
            logger.error(f"Error getting activity statistics: {e}")
            return {
                'total_activities': 0,
                'activities_by_type': {},
                'activities_by_day': {},
                'success_rate': 0,
                'avg_response_time_ms': 0,
                'period_days': days,
                'start_date': None
            }
    
    def cleanup_old_activities(self, days: int = 30) -> int:
        """
        Clean up activities older than specified number of days
        
        Args:
            days: Delete activities older than this many days (default: 30)
            
        Returns:
            Number of activities deleted
        """
        try:
            from datetime import timedelta
            cutoff_datetime = datetime.now() - timedelta(days=days)
            cutoff_timestamp = cutoff_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM activity_logs 
                    WHERE timestamp < ?
                ''', (cutoff_timestamp,))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} activities older than {days} days (before {cutoff_timestamp})")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old activities: {e}")
            return 0
    
    def get_command_usage_stats(self, days: int = 7) -> Dict[str, int]:
        """
        Get command usage statistics for last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with command names and their usage counts
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT command, COUNT(*) as count 
                    FROM activity_logs 
                    WHERE command IS NOT NULL 
                      AND timestamp >= ?
                    GROUP BY command
                    ORDER BY count DESC
                ''', (start_timestamp,))
                
                stats = {row['command']: row['count'] for row in cursor.fetchall()}
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Command usage stats query completed in {query_time}ms")
                return stats
        except Exception as e:
            logger.error(f"Error getting command usage stats: {e}")
            return {}
    
    def get_quiz_performance_stats(self, days: int = 7) -> Dict:
        """
        Get quiz performance metrics for last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with quiz performance metrics including:
            - total_sent: Total quizzes sent
            - total_answered: Total answers received
            - success_rate: Percentage of correct answers
            - avg_response_time_ms: Average response time
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM activity_logs 
                    WHERE activity_type = 'quiz_sent' 
                      AND timestamp >= ?
                      AND (details NOT LIKE '%auto_delete%' OR details IS NULL)
                ''', (start_timestamp,))
                total_sent = cursor.fetchone()['count'] or 0
                
                cursor.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM quiz_history
                    WHERE answered_at >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                total_answered = row['total'] or 0
                correct_answers = row['correct'] or 0
                success_rate = round((correct_answers / max(total_answered, 1)) * 100, 1)
                
                cursor.execute('''
                    SELECT AVG(response_time_ms) as avg_time 
                    FROM activity_logs 
                    WHERE activity_type = 'quiz_answer'
                      AND response_time_ms IS NOT NULL
                      AND timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                avg_response_time = round(row['avg_time'], 2) if row['avg_time'] else 0
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Quiz performance stats query completed in {query_time}ms")
                
                return {
                    'total_sent': total_sent,
                    'total_answered': total_answered,
                    'success_rate': success_rate,
                    'avg_response_time_ms': avg_response_time,
                    'correct_answers': correct_answers,
                    'wrong_answers': total_answered - correct_answers,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f"Error getting quiz performance stats: {e}")
            return {
                'total_sent': 0,
                'total_answered': 0,
                'success_rate': 0,
                'avg_response_time_ms': 0,
                'correct_answers': 0,
                'wrong_answers': 0,
                'period_days': days
            }
    
    def get_user_engagement_stats(self) -> Dict:
        """
        Get user engagement metrics
        
        Returns:
            Dictionary with user engagement metrics including:
            - active_today: Users active today
            - active_week: Users active this week
            - active_month: Users active this month
            - total_users: Total registered users
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')
            week_start = (datetime(now.year, now.month, now.day, 0, 0, 0) - timedelta(days=now.weekday())).strftime('%Y-%m-%d %H:%M:%S')
            month_start = datetime(now.year, now.month, 1, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) as count FROM users')
                total_users = cursor.fetchone()['count']
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) as count 
                    FROM activity_logs 
                    WHERE user_id IS NOT NULL 
                      AND timestamp >= ? AND timestamp <= ?
                ''', (today_start, today_end))
                active_today = cursor.fetchone()['count']
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) as count 
                    FROM activity_logs 
                    WHERE user_id IS NOT NULL 
                      AND timestamp >= ?
                ''', (week_start,))
                active_week = cursor.fetchone()['count']
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) as count 
                    FROM activity_logs 
                    WHERE user_id IS NOT NULL 
                      AND timestamp >= ?
                ''', (month_start,))
                active_month = cursor.fetchone()['count']
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"User engagement stats query completed in {query_time}ms")
                
                return {
                    'active_today': active_today,
                    'active_week': active_week,
                    'active_month': active_month,
                    'total_users': total_users
                }
        except Exception as e:
            logger.error(f"Error getting user engagement stats: {e}")
            return {
                'active_today': 0,
                'active_week': 0,
                'active_month': 0,
                'total_users': 0
            }
    
    def get_hourly_activity_stats(self, hours: int = 24) -> List[Dict]:
        """
        Get activity breakdown by hour for visualization
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of dictionaries with hour and activity_count
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            
            start_datetime = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                        COUNT(*) as activity_count
                    FROM activity_logs 
                    WHERE timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour DESC
                ''', (start_timestamp,))
                
                results = [{'hour': row['hour'], 'activity_count': row['activity_count']} 
                          for row in cursor.fetchall()]
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Hourly activity stats query completed in {query_time}ms")
                return results
        except Exception as e:
            logger.error(f"Error getting hourly activity stats: {e}")
            return []
    
    def get_error_rate_stats(self, days: int = 7) -> Dict:
        """
        Get error statistics for last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with error statistics including:
            - total_errors: Total error count
            - error_rate: Percentage of failed activities
            - common_errors: Most common error types
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                    FROM activity_logs 
                    WHERE timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                total_activities = row['total'] or 0
                total_errors = row['errors'] or 0
                error_rate = round((total_errors / max(total_activities, 1)) * 100, 2)
                
                cursor.execute('''
                    SELECT activity_type, COUNT(*) as count
                    FROM activity_logs 
                    WHERE success = 0 
                      AND timestamp >= ?
                    GROUP BY activity_type
                    ORDER BY count DESC
                    LIMIT 5
                ''', (start_timestamp,))
                common_errors = {row['activity_type']: row['count'] for row in cursor.fetchall()}
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Error rate stats query completed in {query_time}ms")
                
                return {
                    'total_errors': total_errors,
                    'error_rate': error_rate,
                    'common_errors': common_errors,
                    'total_activities': total_activities,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f"Error getting error rate stats: {e}")
            return {
                'total_errors': 0,
                'error_rate': 0,
                'common_errors': {},
                'total_activities': 0,
                'period_days': days
            }
    
    def get_broadcast_stats(self) -> Dict:
        """
        Get broadcast performance from broadcast_logs
        
        Returns:
            Dictionary with broadcast statistics including:
            - total_broadcasts: Total broadcasts sent
            - total_sent: Total messages delivered
            - avg_success_rate: Average delivery success rate
            - total_failed: Total failed deliveries
        """
        try:
            import time
            start_time = time.time()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_broadcasts,
                        SUM(sent_count) as total_sent,
                        SUM(failed_count) as total_failed,
                        SUM(total_targets) as total_targets
                    FROM broadcast_logs
                ''')
                row = cursor.fetchone()
                
                total_broadcasts = row['total_broadcasts'] or 0
                total_sent = row['total_sent'] or 0
                total_failed = row['total_failed'] or 0
                total_targets = row['total_targets'] or 0
                
                avg_success_rate = round((total_sent / max(total_targets, 1)) * 100, 1)
                
                cursor.execute('''
                    SELECT admin_id, COUNT(*) as count
                    FROM broadcast_logs
                    GROUP BY admin_id
                    ORDER BY count DESC
                    LIMIT 5
                ''')
                top_broadcasters = {row['admin_id']: row['count'] for row in cursor.fetchall()}
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Broadcast stats query completed in {query_time}ms")
                
                return {
                    'total_broadcasts': total_broadcasts,
                    'total_sent': total_sent,
                    'total_failed': total_failed,
                    'avg_success_rate': avg_success_rate,
                    'total_targets': total_targets,
                    'top_broadcasters': top_broadcasters
                }
        except Exception as e:
            logger.error(f"Error getting broadcast stats: {e}")
            return {
                'total_broadcasts': 0,
                'total_sent': 0,
                'total_failed': 0,
                'avg_success_rate': 0,
                'total_targets': 0,
                'top_broadcasters': {}
            }
    
    def get_response_time_stats(self, days: int = 7) -> Dict[str, float]:
        """
        Get average response times by command for last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with command names and their average response times in milliseconds
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        command, 
                        AVG(response_time_ms) as avg_time,
                        COUNT(*) as count
                    FROM activity_logs 
                    WHERE command IS NOT NULL 
                      AND response_time_ms IS NOT NULL
                      AND timestamp >= ?
                    GROUP BY command
                    ORDER BY avg_time DESC
                ''', (start_timestamp,))
                
                stats = {row['command']: round(row['avg_time'], 2) for row in cursor.fetchall()}
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Response time stats query completed in {query_time}ms")
                return stats
        except Exception as e:
            logger.error(f"Error getting response time stats: {e}")
            return {}
    
    def get_user_quiz_stats_realtime(self, user_id: int) -> Optional[Dict]:
        """
        Get user's quiz statistics from database in real-time
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with user quiz statistics including:
            - total_quizzes: Total quizzes attempted
            - correct_answers: Number of correct answers
            - success_rate: Percentage of correct answers
            - streak: Current streak (calculated from recent activity)
            - today_quizzes: Quizzes attempted today
            - week_quizzes: Quizzes attempted this week
        """
        try:
            import time
            start_time = time.time()
            from datetime import timedelta
            
            # Use datetime ranges for proper index usage
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get start of week (Monday)
            week_start = (datetime(now.year, now.month, now.day, 0, 0, 0) - timedelta(days=now.weekday())).strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        current_score,
                        total_quizzes,
                        correct_answers,
                        wrong_answers,
                        success_rate
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    return None
                
                # Use timestamp range query for better index usage
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM quiz_history
                    WHERE user_id = ? 
                      AND answered_at >= ? 
                      AND answered_at <= ?
                ''', (user_id, today_start, today_end))
                today_quizzes = cursor.fetchone()['count']
                
                # Use timestamp range query for week
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM quiz_history
                    WHERE user_id = ? 
                      AND answered_at >= ?
                ''', (user_id, week_start))
                week_quizzes = cursor.fetchone()['count']
                
                cursor.execute('''
                    SELECT is_correct, answered_at
                    FROM quiz_history
                    WHERE user_id = ?
                    ORDER BY answered_at DESC
                    LIMIT 50
                ''', (user_id,))
                recent_answers = cursor.fetchall()
                
                streak = 0
                for answer in recent_answers:
                    if answer['is_correct']:
                        streak += 1
                    else:
                        break
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"User quiz stats query completed in {query_time}ms for user {user_id}")
                
                return {
                    'user_id': user_id,
                    'current_score': user_row['current_score'],
                    'total_quizzes': user_row['total_quizzes'],
                    'correct_answers': user_row['correct_answers'],
                    'wrong_answers': user_row['wrong_answers'],
                    'success_rate': round(user_row['success_rate'], 1),
                    'streak': streak,
                    'today_quizzes': today_quizzes,
                    'week_quizzes': week_quizzes
                }
        except Exception as e:
            logger.error(f"Error getting user quiz stats for {user_id}: {e}")
            return None
    
    def get_leaderboard_count(self) -> int:
        """
        Get total count of eligible users for leaderboard (lightweight query)
        
        Returns:
            Total count of users with at least one quiz attempt
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM users WHERE total_quizzes > 0
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting leaderboard count: {e}")
            return 0
    
    def get_leaderboard_realtime(self, limit: int = 10, offset: int = 0, skip_count: bool = False) -> Tuple[List[Dict], int]:
        """
        Get leaderboard from database in real-time with pagination support
        
        Args:
            limit: Number of top users to return (default: 10)
            offset: Number of users to skip (default: 0)
            skip_count: If True, skip COUNT query and return -1 (default: False)
            
        Returns:
            Tuple of (leaderboard data, total count of eligible users or -1 if skipped)
        """
        try:
            import time
            start_time = time.time()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Conditionally get total count based on skip_count flag
                if skip_count:
                    total_count = -1
                    logger.debug(f"Skipping COUNT query for leaderboard (offset={offset}, limit={limit})")
                else:
                    cursor.execute('''
                        SELECT COUNT(*) FROM users WHERE total_quizzes > 0
                    ''')
                    total_count = cursor.fetchone()[0]
                
                # Get the paginated leaderboard data
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.last_name,
                        u.current_score,
                        u.total_quizzes,
                        u.correct_answers,
                        u.wrong_answers,
                        u.success_rate,
                        u.last_activity_date
                    FROM users u
                    WHERE u.total_quizzes > 0
                    ORDER BY u.current_score DESC, u.success_rate DESC, u.total_quizzes DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                leaderboard = []
                for row in cursor.fetchall():
                    username = row['username'] or row['first_name'] or f"User {row['user_id']}"
                    leaderboard.append({
                        'user_id': row['user_id'],
                        'username': username,
                        'first_name': row['first_name'],
                        'score': row['current_score'],
                        'total_quizzes': row['total_quizzes'],
                        'correct_answers': row['correct_answers'],
                        'wrong_answers': row['wrong_answers'],
                        'accuracy': round(row['success_rate'], 1),
                        'last_active': row['last_activity_date']
                    })
                
                query_time = int((time.time() - start_time) * 1000)
                logger.debug(f"Leaderboard query completed in {query_time}ms (offset={offset}, limit={limit}, total={total_count}, skip_count={skip_count})")
                return leaderboard, total_count
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return [], 0
    
    def log_performance_metric(self, metric_type: str, value: float, metric_name: str = None, 
                              unit: str = None, details: dict = None):
        """
        Log performance metric in real-time
        
        Args:
            metric_type: Type of metric ('response_time', 'api_call', 'error_rate', 'memory_usage', 'uptime')
            value: Numeric value of the metric
            metric_name: Optional name/identifier (e.g., '/start', 'telegram_send_message')
            unit: Optional unit ('ms', 'bytes', 'MB', 'percent', 'count')
            details: Optional JSON details for extra context
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            details_json = json.dumps(details) if details else None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO performance_metrics (timestamp, metric_type, metric_name, value, unit, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, metric_type, metric_name, value, unit, details_json))
            
        except Exception as e:
            logger.debug(f"Error logging performance metric (non-critical): {e}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """
        Get performance summary for dashboard
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary with performance metrics including:
            - avg_response_time: Average response time in ms
            - total_api_calls: Total API calls made
            - error_rate: Error rate percentage
            - uptime_percent: Uptime percentage
            - memory_usage_mb: Current/average memory usage
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT AVG(value) as avg_time
                    FROM performance_metrics
                    WHERE metric_type = 'response_time'
                      AND timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                avg_response_time = round(row['avg_time'], 2) if row and row['avg_time'] else 0
                
                cursor.execute('''
                    SELECT SUM(value) as total_calls
                    FROM performance_metrics
                    WHERE metric_type = 'api_call'
                      AND timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                total_api_calls = int(row['total_calls']) if row and row['total_calls'] else 0
                
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN metric_type = 'error' THEN value ELSE 0 END) as errors,
                        COUNT(*) as total_operations
                    FROM performance_metrics
                    WHERE metric_type IN ('error', 'success')
                      AND timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                errors = row['errors'] if row and row['errors'] else 0
                total_ops = row['total_operations'] if row and row['total_operations'] else 0
                error_rate = round((errors / max(total_ops, 1)) * 100, 2)
                
                cursor.execute('''
                    SELECT value, timestamp
                    FROM performance_metrics
                    WHERE metric_type = 'memory_usage'
                      AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (start_timestamp,))
                row = cursor.fetchone()
                memory_usage_mb = round(row['value'], 2) if row and row['value'] else 0
                
                cursor.execute('''
                    SELECT AVG(value) as avg_mem
                    FROM performance_metrics
                    WHERE metric_type = 'memory_usage'
                      AND timestamp >= ?
                ''', (start_timestamp,))
                row = cursor.fetchone()
                avg_memory_mb = round(row['avg_mem'], 2) if row and row['avg_mem'] else 0
                
                uptime_percent = 100.0
                
                return {
                    'avg_response_time': avg_response_time,
                    'total_api_calls': total_api_calls,
                    'error_rate': error_rate,
                    'uptime_percent': uptime_percent,
                    'memory_usage_mb': memory_usage_mb,
                    'avg_memory_mb': avg_memory_mb,
                    'period_hours': hours
                }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {
                'avg_response_time': 0,
                'total_api_calls': 0,
                'error_rate': 0,
                'uptime_percent': 0,
                'memory_usage_mb': 0,
                'avg_memory_mb': 0,
                'period_hours': hours
            }
    
    def get_response_time_trends(self, hours: int = 24) -> List[Dict]:
        """
        Get response time trends by hour
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of dictionaries with hour and avg_response_time
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                        AVG(value) as avg_response_time,
                        COUNT(*) as count
                    FROM performance_metrics
                    WHERE metric_type = 'response_time'
                      AND timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour DESC
                ''', (start_timestamp,))
                
                return [{'hour': row['hour'], 
                        'avg_response_time': round(row['avg_response_time'], 2),
                        'count': row['count']} 
                       for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting response time trends: {e}")
            return []
    
    def get_api_call_counts(self, hours: int = 24) -> Dict:
        """
        Get API call statistics
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary with API call counts by metric_name
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        metric_name,
                        SUM(value) as total_calls
                    FROM performance_metrics
                    WHERE metric_type = 'api_call'
                      AND timestamp >= ?
                    GROUP BY metric_name
                    ORDER BY total_calls DESC
                ''', (start_timestamp,))
                
                return {row['metric_name']: int(row['total_calls']) for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error getting API call counts: {e}")
            return {}
    
    def get_memory_usage_history(self, hours: int = 24) -> List[Dict]:
        """
        Get memory usage over time
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of dictionaries with timestamp and memory_usage_mb
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(hours=hours)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        timestamp,
                        value as memory_usage_mb
                    FROM performance_metrics
                    WHERE metric_type = 'memory_usage'
                      AND timestamp >= ?
                    ORDER BY timestamp ASC
                ''', (start_timestamp,))
                
                return [{'timestamp': row['timestamp'], 
                        'memory_usage_mb': round(row['memory_usage_mb'], 2)} 
                       for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting memory usage history: {e}")
            return []
    
    def cleanup_old_performance_metrics(self, days: int = 7) -> int:
        """
        Clean up performance metrics older than specified days
        
        Args:
            days: Delete metrics older than this many days (default: 7)
            
        Returns:
            Number of metrics deleted
        """
        try:
            from datetime import timedelta
            cutoff_datetime = datetime.now() - timedelta(days=days)
            cutoff_timestamp = cutoff_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM performance_metrics 
                    WHERE timestamp < ?
                ''', (cutoff_timestamp,))
                
                deleted_count = cursor.rowcount
                logger.info(f"Cleaned up {deleted_count} performance metrics older than {days} days")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old performance metrics: {e}")
            return 0
    
    def get_trending_commands(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """
        Get most used commands in the last N days
        
        Args:
            days: Number of days to look back (default: 7)
            limit: Maximum number of commands to return (default: 10)
            
        Returns:
            List of dictionaries with command_name and count
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        details,
                        COUNT(*) as count
                    FROM activity_logs
                    WHERE activity_type = 'command'
                      AND timestamp >= ?
                    GROUP BY details
                    ORDER BY count DESC
                    LIMIT ?
                ''', (start_timestamp, limit))
                
                trending = []
                for row in cursor.fetchall():
                    try:
                        details = json.loads(row['details']) if row['details'] else {}
                        command_name = details.get('command', 'unknown')
                        trending.append({
                            'command': command_name,
                            'count': row['count']
                        })
                    except:
                        continue
                
                logger.debug(f"Retrieved {len(trending)} trending commands for last {days} days")
                return trending
        except Exception as e:
            logger.error(f"Error getting trending commands: {e}")
            return []
    
    def get_active_users_count(self, period: str = 'today') -> int:
        """
        Get count of active users for a specific time period
        
        Args:
            period: Time period - 'today', 'week', 'month' (default: 'today')
            
        Returns:
            Count of active users
        """
        try:
            from datetime import timedelta
            
            now = datetime.now()
            if period == 'today':
                start_timestamp = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            elif period == 'week':
                start_datetime = datetime.now() - timedelta(days=7)
                start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            elif period == 'month':
                start_datetime = datetime.now() - timedelta(days=30)
                start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_timestamp = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM activity_logs
                    WHERE user_id IS NOT NULL
                      AND timestamp >= ?
                ''', (start_timestamp,))
                
                row = cursor.fetchone()
                count = row['count'] if row else 0
                logger.debug(f"Active users {period}: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting active users count for {period}: {e}")
            return 0
    
    def get_new_users(self, days: int = 7) -> List[Dict]:
        """
        Get users who joined in the last N days
        
        Args:
            days: Number of days to look back (default: 7)
            
        Returns:
            List of user dictionaries
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users
                    WHERE joined_at >= ?
                    ORDER BY joined_at DESC
                ''', (start_timestamp,))
                
                users = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"Found {len(users)} new users in last {days} days")
                return users
        except Exception as e:
            logger.error(f"Error getting new users: {e}")
            return []
    
    def get_most_active_users(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get most active users based on recent activity
        
        Args:
            limit: Maximum number of users to return (default: 10)
            days: Number of days to look back (default: 30)
            
        Returns:
            List of user dictionaries with activity counts
        """
        try:
            from datetime import timedelta
            start_datetime = datetime.now() - timedelta(days=days)
            start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.current_score,
                        u.total_quizzes,
                        u.correct_answers,
                        COUNT(a.id) as activity_count
                    FROM users u
                    LEFT JOIN activity_logs a ON u.user_id = a.user_id
                      AND a.timestamp >= ?
                    WHERE u.total_quizzes > 0
                    GROUP BY u.user_id
                    ORDER BY activity_count DESC, u.total_quizzes DESC
                    LIMIT ?
                ''', (start_timestamp, limit))
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'first_name': row['first_name'],
                        'current_score': row['current_score'],
                        'total_quizzes': row['total_quizzes'],
                        'correct_answers': row['correct_answers'],
                        'activity_count': row['activity_count']
                    })
                
                logger.debug(f"Retrieved {len(users)} most active users")
                return users
        except Exception as e:
            logger.error(f"Error getting most active users: {e}")
            return []
    
    def get_quiz_stats_by_period(self, period: str = 'today') -> Dict:
        """
        Get quiz statistics for a specific time period
        
        Args:
            period: Time period - 'today', 'week', 'month', 'all' (default: 'today')
            
        Returns:
            Dictionary with quiz statistics
        """
        try:
            from datetime import timedelta
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if period == 'all':
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as total_sent,
                            SUM(CASE WHEN activity_type = 'quiz_answered' THEN 1 ELSE 0 END) as total_answered
                        FROM activity_logs
                        WHERE activity_type IN ('quiz_sent', 'quiz_answered')
                    ''')
                else:
                    now = datetime.now()
                    if period == 'today':
                        start_timestamp = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
                    elif period == 'week':
                        start_datetime = datetime.now() - timedelta(days=7)
                        start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    elif period == 'month':
                        start_datetime = datetime.now() - timedelta(days=30)
                        start_timestamp = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        start_timestamp = datetime(now.year, now.month, now.day, 0, 0, 0).strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as total_sent,
                            SUM(CASE WHEN activity_type = 'quiz_answered' THEN 1 ELSE 0 END) as total_answered
                        FROM activity_logs
                        WHERE activity_type IN ('quiz_sent', 'quiz_answered')
                          AND timestamp >= ?
                    ''', (start_timestamp,))
                
                row = cursor.fetchone()
                total_sent = row['total_sent'] if row and row['total_sent'] else 0
                total_answered = row['total_answered'] if row and row['total_answered'] else 0
                
                cursor.execute('''
                    SELECT 
                        SUM(correct_answers) as total_correct,
                        SUM(total_quizzes) as total_attempts
                    FROM users
                ''')
                
                row = cursor.fetchone()
                total_correct = row['total_correct'] if row and row['total_correct'] else 0
                total_attempts = row['total_attempts'] if row and row['total_attempts'] else 1
                success_rate = round((total_correct / max(total_attempts, 1)) * 100, 2)
                
                stats = {
                    'quizzes_sent': total_sent,
                    'quizzes_answered': total_answered,
                    'success_rate': success_rate,
                    'period': period
                }
                
                logger.debug(f"Quiz stats for {period}: {stats}")
                return stats
        except Exception as e:
            logger.error(f"Error getting quiz stats for {period}: {e}")
            return {
                'quizzes_sent': 0,
                'quizzes_answered': 0,
                'success_rate': 0,
                'period': period
            }
    
    def migrate_iso_timestamps_to_space_format(self) -> Dict[str, int]:
        """
        Migrate timestamps from ISO format (with 'T') to space-separated format
        This is a one-time migration to fix timestamp format inconsistency
        
        Returns:
            Dictionary with migration counts for each table
        """
        migration_counts = {
            'activity_logs': 0,
            'performance_metrics': 0
        }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Migrate activity_logs timestamps
                cursor.execute("SELECT id, timestamp FROM activity_logs WHERE timestamp LIKE '%T%'")
                rows = cursor.fetchall()
                for row in rows:
                    old_timestamp = row['timestamp']
                    try:
                        # Convert ISO format to space-separated format
                        dt = datetime.fromisoformat(old_timestamp.replace('Z', '+00:00'))
                        new_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                        cursor.execute("UPDATE activity_logs SET timestamp = ? WHERE id = ?", 
                                     (new_timestamp, row['id']))
                        migration_counts['activity_logs'] += 1
                    except Exception as e:
                        logger.error(f"Error migrating activity_logs timestamp {old_timestamp}: {e}")
                
                # Migrate performance_metrics timestamps
                cursor.execute("SELECT id, timestamp FROM performance_metrics WHERE timestamp LIKE '%T%'")
                rows = cursor.fetchall()
                for row in rows:
                    old_timestamp = row['timestamp']
                    try:
                        # Convert ISO format to space-separated format
                        dt = datetime.fromisoformat(old_timestamp.replace('Z', '+00:00'))
                        new_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                        cursor.execute("UPDATE performance_metrics SET timestamp = ? WHERE id = ?", 
                                     (new_timestamp, row['id']))
                        migration_counts['performance_metrics'] += 1
                    except Exception as e:
                        logger.error(f"Error migrating performance_metrics timestamp {old_timestamp}: {e}")
                
                logger.info(f"Timestamp migration completed: {migration_counts}")
                return migration_counts
        except Exception as e:
            logger.error(f"Error during timestamp migration: {e}")
            return migration_counts
    
    @staticmethod
    def format_relative_time(timestamp_str: str) -> str:
        """
        Format timestamp as relative time (e.g., "5 min ago", "2 hours ago")
        
        Args:
            timestamp_str: Timestamp string in ISO format
            
        Returns:
            Formatted relative time string
        """
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now()
            
            if timestamp.tzinfo is not None:
                from datetime import timezone
                now = datetime.now(timezone.utc)
            
            diff = now - timestamp
            seconds = diff.total_seconds()
            
            if seconds < 60:
                return f"{int(seconds)}s ago"
            elif seconds < 3600:
                return f"{int(seconds / 60)}m ago"
            elif seconds < 86400:
                return f"{int(seconds / 3600)}h ago"
            elif seconds < 604800:
                return f"{int(seconds / 86400)}d ago"
            else:
                return timestamp.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error formatting relative time: {e}")
            return "recently"
