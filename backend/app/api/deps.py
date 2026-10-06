from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from app.schemas.user import TokenPayload, UserRole
from app.services.auth_service import AuthService

security_scheme = HTTPBearer()

# In-memory blacklist for revoked tokens (FR-AUTH-04)
# In production, this can be backed by Redis
REVOKED_TOKENS = set()

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> TokenPayload:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti in REVOKED_TOKENS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or logged out",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id_str: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id_str is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenPayload(sub=user_id_str, role=role, jti=jti)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token_payload: TokenPayload = Depends(get_current_user_token)) -> dict:
    user = AuthService.get_user_by_id(int(token_payload.sub))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

class RoleChecker:
    """RBAC Guard verifying if current user's role is in the allowed list."""
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = [r.value if isinstance(r, UserRole) else r for r in allowed_roles]

    def __call__(self, token_payload: TokenPayload = Depends(get_current_user_token)):
        if token_payload.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of [{', '.join(self.allowed_roles)}] privileges"
            )
        return token_payload

# Pre-defined reusable guards for the SRS user classes (SRS Section 4 & 8.1)
require_admin = RoleChecker([UserRole.ADMINISTRATOR])
require_reviewer = RoleChecker([UserRole.ADMINISTRATOR, UserRole.REVIEWER])
require_source_manager = RoleChecker([UserRole.ADMINISTRATOR, UserRole.SOURCE_MANAGER])
require_data_scientist = RoleChecker([UserRole.ADMINISTRATOR, UserRole.DATA_SCIENTIST])
require_coordinator = RoleChecker([UserRole.ADMINISTRATOR, UserRole.INSTITUTION_COORDINATOR])
require_registered_user = RoleChecker([
    UserRole.ADMINISTRATOR, UserRole.REVIEWER, UserRole.SOURCE_MANAGER,
    UserRole.DATA_SCIENTIST, UserRole.INSTITUTION_COORDINATOR, UserRole.USER
])