from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from app.core.database import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(
        String(36),
        primary_key=True,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
