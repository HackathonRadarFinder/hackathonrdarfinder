from fastapi import HTTPException


class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": code,
                    "message": message,
                },
            },
        )


def not_found_error(resource: str):
    return APIError(
        status_code=404,
        code="RESOURCE_NOT_FOUND",
        message=f"{resource} not found",
    )


def already_exists_error(resource: str):
    return APIError(
        status_code=400,
        code="RESOURCE_ALREADY_EXISTS",
        message=f"{resource} already exists",
    )