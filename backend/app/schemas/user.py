
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, Enum):
    VISITOR = "visitor"
    USER = "user"
    INSTITUTION_COORDINATOR = "institution_coordinator"
    REVIEWER = "reviewer"
    SOURCE_MANAGER = "source_manager"
    DATA_SCIENTIST = "data_scientist"
    ADMINISTRATOR = "administrator"


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    # The public registration API must not accept a privileged role.
    password: str = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError(
                "Password must not exceed 72 bytes"
            )
        return value


class UserResponse(UserBase):
    id: UUID
    role: UserRole
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class TokenPayload(BaseModel):
    sub: str
    role: str
    jti: str
    exp: int
