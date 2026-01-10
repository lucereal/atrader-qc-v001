# region imports
from AlgorithmImports import *
# endregion

class PositionFinderException(Exception):
    """Custom exception to be raised when user data is invalid."""
    def __init__(self, message=None, error_code = None, related_fields = None):
        self.error_code = error_code
        self.related_fields = related_fields
        super().__init__(f"PositionFinderException: {message}")
