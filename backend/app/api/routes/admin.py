from fastapi import APIRouter

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/status")
async def admin_status():
    return {
        "message": "Admin API is ready"
    }