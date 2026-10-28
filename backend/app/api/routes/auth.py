
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    TokenPayload,
)
from app.services.auth_service import AuthService
from app.models.revoked_token import RevokedToken
from app.api.deps import (
    get_current_user,
    get_current_user_token,
    require_admin,
    require_reviewer,
    require_source_manager,
    require_data_scientist,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication & RBAC"],
)


@router.get("/status")
async def auth_status():
    return {
        "message": "Authentication API is ready"
    }


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a regular user in the database."""
    return AuthService.register_user(user_in, db)


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """Authenticate a user against the database."""
    user = AuthService.authenticate_user(credentials, db)

    role = AuthService.get_primary_role(user)

    access_token = create_access_token(
        subject=str(user.id),
        role=role,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=role,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user=Depends(get_current_user),
):
    """Return the current authenticated user."""
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    token_data: TokenPayload = Depends(get_current_user_token),
    db: Session = Depends(get_db),
):
    """Persist revocation across restarts and workers sharing the database."""
    db.add(RevokedToken(
        jti=token_data.jti,
        expires_at=datetime.fromtimestamp(token_data.exp, timezone.utc),
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Concurrent logout may have already persisted the same JTI.
        if db.get(RevokedToken, token_data.jti) is None:
            raise

    return {
        "message": "Successfully logged out. Session revoked."
    }


@router.get("/admin-only")
def admin_area(
    token_data: TokenPayload = Depends(require_admin),
):
    return {
        "message": "Admin access granted",
        "role": token_data.role,
    }


@router.get("/reviewer-only")
def reviewer_area(
    token_data: TokenPayload = Depends(require_reviewer),
):
    return {
        "message": "Reviewer access granted",
        "role": token_data.role,
    }


@router.get("/source-manager-only")
def source_manager_area(
    token_data: TokenPayload = Depends(require_source_manager),
):
    return {
        "message": "Source manager access granted",
        "role": token_data.role,
    }


@router.get("/data-scientist-only")
def data_scientist_area(
    token_data: TokenPayload = Depends(require_data_scientist),
):
    return {
        "message": "Data scientist access granted",
        "role": token_data.role,
    }
