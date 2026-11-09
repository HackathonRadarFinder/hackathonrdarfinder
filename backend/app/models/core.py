import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(50), nullable=False, default="active")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        primary_key=True,
    )

    role_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("roles.id"),
        primary_key=True,
    )


class Preference(Base):
    __tablename__ = "preferences"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "key",
            name="uq_preference_user_key",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    key = Column(String(100), nullable=False)
    value = Column(String(255), nullable=True)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(150), nullable=False)
    url = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class EventVersion(Base):
    __tablename__ = "event_versions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    hackathon_id = Column(
        Integer,
        ForeignKey("hackathons.id"),
        nullable=False,
    )

    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)

    title = Column(String(255), nullable=True)
    description = Column(String(1000), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    hackathon = relationship("Hackathon")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    hackathon_id = Column(
        Integer,
        ForeignKey("hackathons.id"),
        nullable=False,
    )

    model_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("models.id"),
        nullable=True,
    )

    prediction = Column(String(255), nullable=True)

    confidence = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    hackathon = relationship("Hackathon")
    model = relationship("Model")


class SavedItem(Base):
    __tablename__ = "saved_items"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "hackathon_id",
            name="uq_saved_item_user_hackathon",
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    hackathon_id = Column(
        Integer,
        ForeignKey("hackathons.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    hackathon = relationship("Hackathon")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=False)

    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Model(Base):
    __tablename__ = "models"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(150), nullable=False)
    version = Column(String(50), nullable=False)
    provider = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Uuid(as_uuid=True), nullable=True)
    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
