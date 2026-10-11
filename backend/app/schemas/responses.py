"""Shared success envelopes and the existing global error contract."""
from typing import Annotated, Generic, TypeVar

from fastapi import Path
from pydantic import BaseModel

from app.schemas.errors import ErrorResponse

T = TypeVar("T")
DatabaseId = Annotated[int, Path(gt=0, le=2_147_483_647)]
ERROR_RESPONSES = {
    status: {"model": ErrorResponse}
    for status in (400, 401, 403, 404, 409, 422, 503)
}


class MessageResponse(BaseModel):
    message: str


class DataResponse(MessageResponse, Generic[T]):
    data: T


class AdminDataResponse(BaseModel, Generic[T]):
    data: T
