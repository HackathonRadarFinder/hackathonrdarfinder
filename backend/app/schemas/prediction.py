from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PredictionBase(BaseModel):
    organization: str
    predicted_date: datetime
    confidence: float
    reasoning: Optional[str] = None


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    id: int

    class Config:
        from_attributes = True
