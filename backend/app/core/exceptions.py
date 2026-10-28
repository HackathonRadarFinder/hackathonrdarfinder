class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict | list | str | None = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code

        super().__init__(message)