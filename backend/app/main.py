from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — register SQLAlchemy models at startup
from app.api.v1 import router as v1_router

app = FastAPI(
    title="VoyageAI API",
    description="AI-powered travel planning platform",
    version="0.1.0",
)

from app.core.config import get_settings

settings = get_settings()

cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

# CORS — configure allowed origins dynamically
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routes
app.include_router(v1_router)


@app.get("/", tags=["Root"])
def root():
    return {"message": "VoyageAI Backend Running 🚀"}