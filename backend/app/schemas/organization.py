from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import Optional


class OrganizationBase(BaseModel):
    name: str
    website: Optional[HttpUrl] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
