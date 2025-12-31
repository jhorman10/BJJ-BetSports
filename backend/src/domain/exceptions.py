"""
Domain exceptions for the prediction system.
"""

class PredictionException(Exception):
    """Base exception for prediction-related errors."""
    pass

class InsufficientDataException(PredictionException):
    """Exception raised when there is not enough historical data to generate a reliable prediction."""
    pass
