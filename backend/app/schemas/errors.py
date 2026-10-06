from datetime import datetime

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | list | str | None = None
    request_id: str
    timestamp: datetime