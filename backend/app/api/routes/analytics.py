from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import AnalyticsSummary
from app.schemas.responses import ERROR_RESPONSES
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"], responses=ERROR_RESPONSES)


@router.get("", response_model=AnalyticsSummary)
@router.get("/summary", response_model=AnalyticsSummary, include_in_schema=False)
def analytics_summary(db: Session = Depends(get_db)):
    """Public aggregate counts only; no user or contact data."""
    return analytics_service.get_analytics_summary(db)
