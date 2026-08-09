from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router

app = FastAPI(
    title="VoyageAI API",
    description="AI-powered travel planning platform",
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routes
app.include_router(v1_router)


@app.get("/", tags=["Root"])
def root():
    return {"message": "VoyageAI Backend Running 🚀"}