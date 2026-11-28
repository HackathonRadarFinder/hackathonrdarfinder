from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StartupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str | None = None
    country: str | None = None


class InvestmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investor_id: int | None = None
    fund: FundResponse | None = None
    startup: StartupResponse
    stage: str | None = None
    check_size: Decimal | Literal["unknown"] = "unknown"
    check_currency: str | None = None
    check_source_url: str | None = None
    round_amount: Decimal | Literal["unknown"] = "unknown"
    round_currency: str | None = None
    round_source_url: str | None = None

    @field_validator("check_size", "round_amount", mode="before")
    @classmethod
    def undisclosed_amount(cls, value):
        return "unknown" if value is None else value


class InvestorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    funds: list[FundResponse] = Field(default_factory=list)


class InvestorDetailResponse(InvestorResponse):
    portfolio: list[InvestmentResponse] = Field(default_factory=list)
