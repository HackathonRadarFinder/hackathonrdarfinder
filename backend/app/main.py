from fastapi import FastAPI

from app.api.routes import (
    events,
    organizations,
    predictions,
    auth,
    notifications,
    admin,
)

app = FastAPI(
    title="Hackathon Radar AI",
    description="Backend API for Hackathon Radar Finder",
    version="0.1.0",
)

app.include_router(events.router)
app.include_router(organizations.router)
app.include_router(predictions.router)
app.include_router(auth.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "hackathon-radar-api",
        "version": "0.1.0",
    }