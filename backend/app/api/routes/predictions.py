from fastapi import APIRouter

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"]
)


@router.get("/")
async def get_predictions():
    return {
        "message": "Predictions API is ready",
        "data": []
    }