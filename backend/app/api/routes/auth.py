from fastapi import APIRouter, status, Depends
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, TokenPayload
from app.services.auth_service import AuthService
from app.core.security import create_access_token
from app.api.deps import (
    get_current_user,
    get_current_user_token,
    REVOKED_TOKENS,
    require_admin,
    require_reviewer,
    require_source_manager,
    require_data_scientist
)

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate):
    """Register a new user account with assigned role (defaults to 'user')."""
    return AuthService.register_user(user_in)

@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    """Authenticate credentials and return JWT containing user role."""
    user = AuthService.authenticate_user(credentials)
    access_token = create_access_token(subject=user["id"], role=user["role"])
    return Token(access_token=access_token, token_type="bearer", role=user["role"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(token_data: TokenPayload = Depends(get_current_user_token)):
    """Revoke active JWT token session (SRS FR-AUTH-04)."""
    if token_data.jti:
        REVOKED_TOKENS.add(token_data.jti)
    return {"message": "Successfully logged out. Session revoked."}

# Verification endpoints proving RBAC enforcement for the 7 roles:
@router.get("/admin-only")
def admin_area(token_data: TokenPayload = Depends(require_admin)):
    return {"message": "Admin access granted", "role": token_data.role}

@router.get("/reviewer-only")
def reviewer_area(token_data: TokenPayload = Depends(require_reviewer)):
    return {"message": "Reviewer access granted", "role": token_data.role}

@router.get("/source-manager-only")
def source_manager_area(token_data: TokenPayload = Depends(require_source_manager)):
    return {"message": "Source manager access granted", "role": token_data.role}

@router.get("/data-scientist-only")
def data_scientist_area(token_data: TokenPayload = Depends(require_data_scientist)):
    return {"message": "Data scientist access granted", "role": token_data.role}