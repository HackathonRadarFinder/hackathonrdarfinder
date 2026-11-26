from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.investor import Investment, Investor, Startup, investor_funds
from app.schemas.investor import InvestorDetailResponse, InvestorResponse
from app.schemas.responses import DatabaseId, DataResponse, ERROR_RESPONSES


router = APIRouter(prefix="/investors", tags=["Investors"], responses=ERROR_RESPONSES)
FilterText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class PortfolioFilters(BaseModel):
    industry: FilterText | None = None
    country: FilterText | None = None
    stage: FilterText | None = None
    portfolio: FilterText | None = None


def matching_investments(investor_id, filters: PortfolioFilters):
    affiliated_funds = select(investor_funds.c.fund_id).where(
        investor_funds.c.investor_id == investor_id
    ).correlate(Investor)
    statement = select(Investment).join(Investment.startup).where(
        or_(Investment.investor_id == investor_id, Investment.fund_id.in_(affiliated_funds))
    )
    for column, value in (
        (Startup.industry, filters.industry),
        (Startup.country, filters.country),
        (Investment.stage, filters.stage),
        (Startup.name, filters.portfolio),
    ):
        if value is not None:
            statement = statement.where(func.lower(column) == value.lower())
    return statement


@router.get("", response_model=DataResponse[list[InvestorResponse]])
def list_investors(filters: Annotated[PortfolioFilters, Query()], db: Session = Depends(get_db)):
    statement = select(Investor).options(selectinload(Investor.funds)).order_by(Investor.id)
    if filters.model_fields_set:
        statement = statement.where(matching_investments(Investor.id, filters).exists())
    return {"message": "Investors fetched successfully", "data": db.scalars(statement).all()}


@router.get("/{investor_id}", response_model=DataResponse[InvestorDetailResponse])
def get_investor(
    investor_id: DatabaseId, filters: Annotated[PortfolioFilters, Query()], db: Session = Depends(get_db)
):
    investor = db.scalar(select(Investor).options(selectinload(Investor.funds)).where(
        Investor.id == investor_id
    ))
    if investor is None:
        raise AppException("investor_not_found", "Investor not found", status_code=404)

    portfolio = db.scalars(matching_investments(investor_id, filters).options(
        selectinload(Investment.startup), selectinload(Investment.fund)
    ).order_by(Investment.id)).all()
    return {
        "message": "Investor fetched successfully",
        "data": {"id": investor.id, "name": investor.name, "funds": investor.funds,
                 "portfolio": portfolio},
    }
