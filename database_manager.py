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
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
                CREATE INDEX IF NOT EXISTS idx_user_activity_date 
                ON user_daily_activity(user_id, activity_date)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_quiz_history_user 
                ON quiz_history(user_id, answered_at)
            ''')
            
            logger.info("Database schema initialized successfully")
    
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
        """Get comprehensive statistics summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            week_start = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - 
                         __import__('datetime').timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
            month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            cursor.execute('SELECT COUNT(*) as count FROM questions')
            total_questions = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM users')
            total_users = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM groups WHERE is_active = 1')
            total_groups = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT SUM(attempts) as count 
                FROM user_daily_activity 
                WHERE activity_date = ?
            ''', (today,))
            quizzes_today = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT SUM(attempts) as count 
                FROM user_daily_activity 
                WHERE activity_date >= ?
            ''', (week_start,))
            quizzes_week = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT SUM(attempts) as count 
                FROM user_daily_activity 
                WHERE activity_date >= ?
            ''', (month_start,))
            quizzes_month = cursor.fetchone()['count'] or 0
            
            cursor.execute('SELECT SUM(total_quizzes) as count FROM users')
            quizzes_alltime = cursor.fetchone()['count'] or 0
            
            cursor.execute('SELECT SUM(correct_answers) as count FROM users')
            correct_alltime = cursor.fetchone()['count'] or 0
            
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count 
                FROM user_daily_activity 
                WHERE activity_date = ?
            ''', (today,))
            active_users_today = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count 
                FROM user_daily_activity 
                WHERE activity_date >= ?
            ''', (week_start,))
            active_users_week = cursor.fetchone()['count']
            
            return {
                'total_questions': total_questions,
                'total_users': total_users,
                'total_groups': total_groups,
                'quizzes_today': quizzes_today,
                'quizzes_week': quizzes_week,
                'quizzes_month': quizzes_month,
                'quizzes_alltime': quizzes_alltime,
                'correct_alltime': correct_alltime,
                'success_rate': round((correct_alltime / max(quizzes_alltime, 1) * 100), 1),
                'active_users_today': active_users_today,
                'active_users_week': active_users_week,
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
