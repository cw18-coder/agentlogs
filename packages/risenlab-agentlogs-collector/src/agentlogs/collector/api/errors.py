import datetime as dt

class APIError(Exception):
    pass

class NotFoundError(APIError):
    pass

class RecoverableError(APIError):
    pass

class MaxAttemptsRecoverableError(RecoverableError):
    max_attempts: int

    def __init__(self, message: str, max_attempts: int):
        self.max_attempts = max_attempts
        super().__init__(message)

class RateLimitError(APIError):
    pass

class NoAvailableTokenError(APIError):
    reset_time: dt.datetime

    def __init__(self, reset_time: dt.datetime):
        self.reset_time = reset_time
        super().__init__("No available tokens, retry after reset time")