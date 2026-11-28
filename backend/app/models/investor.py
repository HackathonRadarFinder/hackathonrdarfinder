"""Individuals, fund affiliations, and investments disclosed by public sources."""
from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Table, Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


investor_funds = Table(
    "investor_funds",
    Base.metadata,
    Column("investor_id", ForeignKey("investors.id"), primary_key=True),
    Column("fund_id", ForeignKey("funds.id"), primary_key=True, index=True),
)


class Investor(Base):
    __tablename__ = "investors"
    __table_args__ = (Index("ix_investors_normalized_name", "normalized_name"), Index("ix_investors_country", "country"))

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # v4.1 additions (INT-01). All nullable: NULL means "unknown", never guessed.
    normalized_name = Column(String(255))
    website = Column(String(500))
    source_url = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    last_updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    merged_into_id = Column(ForeignKey("investors.id", name="fk_investors_merged_into_id"))  # set when a duplicate is merged into another record
    country = Column(String(100))
    region = Column(String(100))
    city = Column(String(150))
    contact_channels = Column(JSON)  # public channels only
    industries = Column(JSON)
    stages = Column(JSON)

    funds = relationship("Fund", secondary=investor_funds, back_populates="investors",
                         order_by="Fund.id")


class Fund(Base):
    __tablename__ = "funds"
    __table_args__ = (Index("ix_funds_normalized_name", "normalized_name"), Index("ix_funds_country", "country"))

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # v4.1 additions (INT-01). All nullable: NULL means "unknown", never guessed.
    normalized_name = Column(String(255))
    website = Column(String(500))
    source_url = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    last_updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    merged_into_id = Column(ForeignKey("funds.id", name="fk_funds_merged_into_id"))  # set when a duplicate is merged into another record
    country = Column(String(100))
    region = Column(String(100))
    city = Column(String(150))
    contact_channels = Column(JSON)  # public channels only
    industries = Column(JSON)
    stages = Column(JSON)
    kind = Column(String(20))  # firm or fund

    investors = relationship("Investor", secondary=investor_funds, back_populates="funds")


class Startup(Base):
    __tablename__ = "startups"
    __table_args__ = (Index("ix_startups_normalized_name", "normalized_name"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(255))
    country = Column(String(255))
    # v4.1 additions (INT-01). All nullable: NULL means "unknown", never guessed.
    normalized_name = Column(String(255))
    website = Column(String(500))
    source_url = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    last_updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    merged_into_id = Column(ForeignKey("startups.id", name="fk_startups_merged_into_id"))  # set when a duplicate is merged into another record


class Investment(Base):
    __tablename__ = "investments"
    __table_args__ = (
        CheckConstraint(
            "(investor_id IS NULL) <> (fund_id IS NULL)",
            name="ck_investments_one_investing_party",
        ),
        CheckConstraint(
            "check_size IS NULL OR (check_size >= 0 AND "
            "NULLIF(TRIM(check_currency), '') IS NOT NULL AND "
            "NULLIF(TRIM(check_source_url), '') IS NOT NULL)",
            name="ck_investments_sourced_check",
        ),
        CheckConstraint(
            "round_amount IS NULL OR (round_amount >= 0 AND "
            "NULLIF(TRIM(round_currency), '') IS NOT NULL AND "
            "NULLIF(TRIM(round_source_url), '') IS NOT NULL)",
            name="ck_investments_sourced_round",
        ),
        Index("ix_investments_announced_on", "announced_on"),
    )

    id = Column(Integer, primary_key=True)
    investor_id = Column(ForeignKey("investors.id"), index=True)
    fund_id = Column(ForeignKey("funds.id"), index=True)
    startup_id = Column(ForeignKey("startups.id"), index=True, nullable=False)
    stage = Column(String(100))
    check_size = Column(Numeric(20, 4))
    check_currency = Column(String(3))
    check_source_url = Column(String(2048))
    round_amount = Column(Numeric(20, 4))
    round_currency = Column(String(3))
    round_source_url = Column(String(2048))
    # v4.1 additions (INT-01)
    announced_on = Column(Date)
    co_investors = Column(JSON)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    source_evidence_id = Column(Uuid(as_uuid=True), ForeignKey("source_evidence.id", name="fk_investments_source_evidence_id"))

    startup = relationship("Startup")
    fund = relationship("Fund")
