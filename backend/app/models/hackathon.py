from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

# JSONB on PostgreSQL, plain JSON elsewhere (the test-suite runs on SQLite).
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=True
    )

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    registration_deadline = Column(DateTime, nullable=True)

    location = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)

    prize = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    url = Column(String(500), nullable=True)
    source = Column(String(100), nullable=True)
    scraped_at = Column(DateTime, nullable=True)

    state = Column(String(100), index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), index=True)
    registration_url = Column(String(500))
    eligibility = Column(Text)

    # --- BAC-02: v4.1 fields (all nullable/defaulted so old rows keep working) ---
    category = Column(String(30), nullable=True, index=True)
    tags = Column(JsonType, nullable=False, server_default=text("'[]'"))
    timezone = Column(String(64), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    fees = Column(String(100), nullable=True)
    lifecycle_state = Column(String(20), nullable=False, server_default="upcoming", index=True)
    contacts = Column(JsonType, nullable=True)

    organization = relationship("Organization")