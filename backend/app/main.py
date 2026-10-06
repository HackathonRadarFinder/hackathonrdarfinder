from fastapi import FastAPI
from app.api.routes.auth import router as auth_router

app = FastAPI(title="Hackathon Radar AI API", version="1.0.0")

# Include the auth routes under /api/v1
app.include_router(auth_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "ok", "app": "Hackathon Radar AI"}