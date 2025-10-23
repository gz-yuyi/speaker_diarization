import os
from datetime import datetime

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


@app.get("/health")
async def health_check():
    redis_status = {
        "status": "healthy",
        "details": "Redis connection successful"
    }
    storage_status = {
        "status": "healthy",
        "details": []
    }
    overall_healthy = True

    # Check Redis connectivity
    try:
        client = redis.from_url(settings.redis_url)
        client.ping()
    except Exception as exc:
        overall_healthy = False
        redis_status = {
            "status": "unhealthy",
            "details": str(exc)
        }

    # Check storage directories
    storage_directories = {
        "base": settings.storage_base_path_obj,
        "uploads": settings.storage_base_path_obj / "uploads",
        "processed": settings.storage_base_path_obj / "processed",
        "temp": settings.storage_base_path_obj / "temp",
    }

    for name, path in storage_directories.items():
        exists = path.exists()
        is_dir = path.is_dir()
        writable = os.access(path, os.W_OK)

        storage_status["details"].append(
            {
                "name": name,
                "path": str(path),
                "exists": exists,
                "is_directory": is_dir,
                "writable": writable,
            }
        )

        if not all([exists, is_dir, writable]):
            overall_healthy = False
            storage_status["status"] = "unhealthy"

    status_code = 200 if overall_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "redis": redis_status,
                "storage": storage_status,
            },
            "version": app.version,
        },
    )
