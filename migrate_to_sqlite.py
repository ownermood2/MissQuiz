"""
Migration script to move from JSON files to SQLite database
"""

import logging
from database_manager import DatabaseManager
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Run migration from JSON to SQLite"""
    try:
        logger.info("Starting migration from JSON to SQLite...")
        
        db = DatabaseManager(config.DATABASE_PATH)
        
        # Migrate all data
        success = db.migrate_from_json(
            questions_file='data/questions.json',
            users_file='data/user_stats.json',
            developers_file='data/developers.json',
            chats_file='data/active_chats.json'
        )
        
        if success:
            logger.info("✅ Migration completed successfully!")
            
            # Show summary
            stats = db.get_stats_summary()
            logger.info(f"📊 Migration Summary:")
            logger.info(f"  Questions: {stats['total_questions']}")
            logger.info(f"  Users: {stats['total_users']}")
            logger.info(f"  Groups: {stats['total_groups']}")
            logger.info(f"  All-time quizzes: {stats['quizzes_alltime']}")
        else:
            logger.error("❌ Migration failed!")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    migrate()
