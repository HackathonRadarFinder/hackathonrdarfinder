from fastapi import FastAPI

from app.database import Base, engine
from app.routers.sources import router as sources_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Hackathon Radar Finder - Source Registry",
    description="API for managing event data collection sources.",
    version="1.0.0"
)


app.include_router(sources_router)


@app.get("/")
def root():
    return {
        "message": "Hackathon Radar Finder Source Registry API",
        "status": "running"
    }