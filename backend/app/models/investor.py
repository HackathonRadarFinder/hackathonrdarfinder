"""Individuals, fund affiliations, and investments disclosed by public sources."""
from sqlalchemy import (
    CheckConstraint, Column, ForeignKey, Integer, Numeric, String, Table,
)
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

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    funds = relationship("Fund", secondary=investor_funds, back_populates="investors",
                         order_by="Fund.id")


class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    investors = relationship("Investor", secondary=investor_funds, back_populates="funds")


class Startup(Base):
    __tablename__ = "startups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(255))
    country = Column(String(255))


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

    startup = relationship("Startup")
    fund = relationship("Fund")
