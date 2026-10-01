from fastapi import APIRouter

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get("/")
async def get_notifications():
    return {
        "message": "Notifications API is ready",
        "data": []
    }