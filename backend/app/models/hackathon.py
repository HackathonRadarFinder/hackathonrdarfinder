from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, true
from sqlalchemy.orm import relationship
from app.core.database import Base


class Hackathon(Base):
    __tablename__ = "hackathons"
    __table_args__ = (
        Index("ix_hackathons_category", "category"),
        Index("ix_hackathons_country", "country"),
        Index("ix_hackathons_lifecycle_state", "lifecycle_state"),
        Index("ix_hackathons_category_start_date", "category", "start_date"),
        Index("ix_hackathons_country_state", "country", "state"),
    )

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

    # v4.1 fields (SRS HAC-01..HAC-04). NULL means "unknown"; never guessed or back-filled.
    category = Column(String(30))  # college, corporate, community, government, startup, other
    tags = Column(JSON)
    technologies = Column(JSON)
    timezone = Column(String(64))  # IANA name of the event's local timezone
    country = Column(String(100))
    city = Column(String(150))
    lifecycle_state = Column(String(20))  # upcoming, active, completed, cancelled
    fee_details = Column(String(255))
    first_seen_at = Column(DateTime)
    last_seen_at = Column(DateTime)
    last_checked_at = Column(DateTime)
    evidence_url = Column(String(500))
    verification_method = Column(String(100))
    verified_at = Column(DateTime)
    unpublished_reason = Column(String(100))  # machine-readable reason code
    is_published = Column(Boolean, nullable=False, server_default=true())

    organization = relationship("Organization")
