from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints
from typing import Annotated, Optional


class OrganizationBase(BaseModel):
    name: str
    website: Optional[HttpUrl] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    website: HttpUrl | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class OrganizationResponse(BaseModel):
    # Existing rows may contain legacy URLs; validate URLs on writes only.
    id: int
    name: str
    website: str | None = None
    industry: str | None = None
    location: str | None = None
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)
