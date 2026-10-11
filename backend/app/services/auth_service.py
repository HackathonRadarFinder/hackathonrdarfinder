
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_password_hash, verify_password
from app.models.core import Role, User
from app.schemas.user import UserCreate, UserLogin


class AuthService:
    @staticmethod
    def register_user(user_in: UserCreate, db: Session) -> dict:
        email = str(user_in.email).strip().lower()

        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        # Public registration always creates a regular user.
        # Clients cannot choose privileged roles.
        default_role = db.scalar(
            select(Role).where(Role.name == "user")
        )

        if default_role is None:
            default_role = Role(name="user")
            db.add(default_role)

        user = User(
            name=user_in.name.strip(),
            email=email,
            password_hash=get_password_hash(user_in.password),
            status="active",
        )

        user.roles.append(default_role)
        db.add(user)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration conflict. Please retry.",
            )

        db.refresh(user)

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": "user",
            "created_at": user.created_at,
        }

    @staticmethod
    def authenticate_user(
        credentials: UserLogin,
        db: Session,
    ) -> User:
        email = str(credentials.email).strip().lower()

        user = db.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email)
        )

        if (
            user is None
            or not verify_password(
                credentials.password,
                user.password_hash,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        return user

    @staticmethod
    def get_user_by_id(
        user_id: UUID,
        db: Session,
    ) -> User | None:
        return db.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )

    @staticmethod
    def get_primary_role(user: User) -> str:
        role_names = {role.name for role in user.roles}

        priority = (
            "administrator",
            "reviewer",
            "source_manager",
            "data_scientist",
            "institution_coordinator",
            "user",
            "visitor",
        )

        for role in priority:
            if role in role_names:
                return role

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No valid role assigned to account",
        )

