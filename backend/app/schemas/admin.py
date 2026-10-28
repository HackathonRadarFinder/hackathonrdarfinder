from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminStats(BaseModel):
    total_events: int
    total_organizations: int
    total_users: int


class AdminUserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    status: str
    created_at: datetime | None
    roles: list[str]
