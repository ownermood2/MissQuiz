"""
Custom exceptions for the Quiz Bot application.
Provides a hierarchy of exceptions for better error handling and debugging.
"""


class QuizBotError(Exception):
    """Base exception for all quiz bot errors"""
    pass


class ConfigurationError(QuizBotError, ValueError):
    """Raised when configuration is invalid or missing"""
    pass


class DatabaseError(QuizBotError):
    """Raised when database operations fail"""
    pass


class QuestionNotFoundError(QuizBotError):
    """Raised when no questions are available"""
    pass


class ValidationError(QuizBotError):
    """Raised when input validation fails"""
    pass
