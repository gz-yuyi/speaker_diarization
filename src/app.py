from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.core.config import settings
from src.core.logger import log

app = FastAPI(
    title="Speaker Diarization API",
    description="API for speaker diarization using pyannote",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    log.info("Speaker Diarization API started")


@app.on_event("shutdown")
async def shutdown_event():
    log.info("Speaker Diarization API shutting down")


@app.get("/")
async def root():
    return {"message": "Speaker Diarization API", "version": "0.1.0"}