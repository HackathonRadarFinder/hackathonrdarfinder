"""Translate database failures through the application's existing handlers."""
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException


@contextmanager
def database_operation(
    db: Session,
    conflict_message: str = "Operation conflicts with related records",
    conflict_status: int = 409,
):
    try:
        yield
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=conflict_status, detail=conflict_message) from None
    except SQLAlchemyError:
        db.rollback()
        # Neither SQL text nor database credentials/parameters belong in a response.
        raise AppException(
            code="DATABASE_ERROR",
            message="Unable to complete database operation.",
            status_code=503,
        ) from None
