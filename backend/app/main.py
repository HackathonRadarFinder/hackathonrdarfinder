from fastapi import FastAPI

app = FastAPI(
    title="Hackathon Radar AI",
    description="AI-powered hackathon discovery and intelligence platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "hackathon-radar-api",
        "version": "0.1.0",
    }