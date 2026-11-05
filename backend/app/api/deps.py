
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.core import User
from app.models.revoked_token import RevokedToken
from app.schemas.user import TokenPayload, UserRole
from app.services.auth_service import AuthService


security_scheme = HTTPBearer()

def unauthorized(detail: str = "Could not validate credentials"):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(
        security_scheme
    ),
    db: Session = Depends(get_db),
) -> TokenPayload:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "require": ["exp", "sub", "jti", "type"]
            },
        )

        if payload.get("type") != "access":
            unauthorized()

        subject = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not isinstance(subject, str):
            unauthorized()

        if not isinstance(role, str) or not role:
            unauthorized()

        if not isinstance(jti, str) or not jti or len(jti) > 36:
            unauthorized()

        expiration = payload.get("exp")
        if type(expiration) is not int:
            unauthorized()

        # Confirm the subject is a valid UUID.
        UUID(subject)

        if db.get(RevokedToken, jti) is not None:
            unauthorized("Session has been revoked")
        token_version = payload.get("tv", 0)  # Legacy tokens predate OTP resets.
        if type(token_version) is not int or token_version < 0:
            unauthorized()
        account = db.get(User, UUID(subject))
        if account is None or account.token_version != token_version:
            unauthorized("Session was invalidated by a password reset")

        return TokenPayload(
            sub=subject,
            role=role,
            jti=jti,
            exp=expiration,
        )

    except (jwt.PyJWTError, ValueError, TypeError):
        unauthorized()


def get_current_db_user(
    token_data: TokenPayload = Depends(
        get_current_user_token
    ),
    db: Session = Depends(get_db),
) -> User:
    user = AuthService.get_user_by_id(
        UUID(token_data.sub),
        db,
    )

    if user is None:
        unauthorized("User not found")

    if user.status != "active":
        unauthorized("Account is inactive")

    return user


def get_current_user(
    user: User = Depends(get_current_db_user),
) -> dict:
    # Resolve the current role from the database.
    role = AuthService.get_primary_role(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role,
        "created_at": user.created_at,
    }


class RoleChecker:
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = {
            role.value if isinstance(role, UserRole) else role
            for role in allowed_roles
        }

    def __call__(
        self,
        user: User = Depends(get_current_db_user),
        token_data: TokenPayload = Depends(
            get_current_user_token
        ),
    ) -> TokenPayload:
        # Always read permissions from the database.
        current_roles = {
            role.name for role in user.roles
        }

        if not current_roles.intersection(
            self.allowed_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return TokenPayload(
            sub=str(user.id),
            role=AuthService.get_primary_role(user),
            jti=token_data.jti,
            exp=token_data.exp,
        )


require_admin = RoleChecker([
    UserRole.ADMINISTRATOR,
])

require_reviewer = RoleChecker([
    UserRole.ADMINISTRATOR,
    UserRole.REVIEWER,
])

require_source_manager = RoleChecker([
    UserRole.ADMINISTRATOR,
    UserRole.SOURCE_MANAGER,
])

require_data_scientist = RoleChecker([
    UserRole.ADMINISTRATOR,
    UserRole.DATA_SCIENTIST,
])

require_coordinator = RoleChecker([
    UserRole.ADMINISTRATOR,
    UserRole.INSTITUTION_COORDINATOR,
])

require_registered_user = RoleChecker([
    UserRole.ADMINISTRATOR,
    UserRole.REVIEWER,
    UserRole.SOURCE_MANAGER,
    UserRole.DATA_SCIENTIST,
    UserRole.INSTITUTION_COORDINATOR,
    UserRole.USER,
])
