from enum import Enum
from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

class UserRole(str, Enum):
    VISITOR = "visitor"
    USER = "user"
    INSTITUTION_COORDINATOR = "institution_coordinator"
    REVIEWER = "reviewer"
    SOURCE_MANAGER = "source_manager"
    DATA_SCIENTIST = "data_scientist"
    ADMINISTRATOR = "administrator"

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.USER  # Defaults to standard student/user

class UserResponse(UserBase):
    id: int
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
    sub: str | None = None
    role: str | None = None
    jti: str | None = None  # Unique token ID for logout/revocation tracking