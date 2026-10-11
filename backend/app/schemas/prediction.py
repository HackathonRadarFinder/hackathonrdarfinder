from pydantic import BaseModel
from typing import List, Optional


class PredictionRequest(BaseModel):
    organization: str
    historical_dates: List[str]


class PredictionResponse(BaseModel):
    organization: str
    predicted_date: Optional[str] = None
    confidence: float
    reasoning: str
