from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Hackathon(Base):
    __tablename__ = "hackathons"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False, index=True)

    organization_id = Column(
         UUID(as_uuid=True),
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

    organization = relationship("Organization")
