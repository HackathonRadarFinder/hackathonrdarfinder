from fastapi import HTTPException, status
from app.schemas.user import UserCreate, UserLogin, UserRole
from app.core.security import get_password_hash, verify_password

USERS_TABLE: dict[str, dict] = {}
USER_ID_COUNTER = 1

class AuthService:
    @staticmethod
    def register_user(user_in: UserCreate) -> dict:
        global USER_ID_COUNTER
        if user_in.email in USERS_TABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )
        
        user_record = {
            "id": USER_ID_COUNTER,
            "name": user_in.name,
            "email": user_in.email,
            "role": user_in.role.value if hasattr(user_in.role, 'value') else user_in.role,
            "hashed_password": get_password_hash(user_in.password),
        }
        USERS_TABLE[user_in.email] = user_record
        USER_ID_COUNTER += 1
        return user_record

    @staticmethod
    def authenticate_user(credentials: UserLogin) -> dict:
        user = USERS_TABLE.get(credentials.email)
        if not user or not verify_password(credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    @staticmethod
    def get_user_by_id(user_id: int) -> dict | None:
        for user in USERS_TABLE.values():
            if user["id"] == user_id:
                return user
        return None