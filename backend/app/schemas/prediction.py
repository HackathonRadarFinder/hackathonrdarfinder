from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class PredictionRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=255)
    historical_dates: List[str] = Field(max_length=1000)

    @field_validator("organization")
    @classmethod
    def nonblank_organization(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Organization must not be blank")
        return value

    @field_validator("historical_dates")
    @classmethod
    def historical_iso_dates(cls, values):
        today = datetime.now(timezone.utc).date()
        for value in values:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
            if parsed.isoformat() != value or parsed > today:
                raise ValueError("History requires past or current ISO calendar dates")
        return sorted(set(values))


class PredictionResponse(BaseModel):
    organization: str
    predicted_date: Optional[str] = None
    confidence: float
    reasoning: str
