import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.models import (
    TaskCreateResponse,
    TaskStatus,
    DetailedMetadata
)
from src.core.config import settings
from src.core.logger import log
from src.services.file_manager import FileManager
from src.services.task_manager import TaskManager

router = APIRouter()
file_manager = FileManager()
task_manager = TaskManager()


@router.post("/diarize/upload", response_model=TaskCreateResponse)
async def upload_audio(
    audio_file: UploadFile = File(...),
    callback_url: Optional[str] = None
):
    """Upload audio file and start diarization task"""

    # Validate file format
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = Path(audio_file.filename).suffix.lower().lstrip('.')
    if file_ext not in settings.supported_formats_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported formats: {', '.join(settings.supported_formats_list)}"
        )

    # Validate file size
    if audio_file.size and audio_file.size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Save uploaded file
    file_path = await file_manager.save_upload(task_id, audio_file)

    # Initialize task record before starting async processing
    task_manager.create_task(
        task_id,
        initial_data={
            "status": "queued",
            "message": "File uploaded. Awaiting processing.",
            "progress": "0",
            "original_filename": audio_file.filename,
            "callback_url": callback_url or "",
        }
    )

    # Start processing task
    from src.workers.tasks import process_audio_task
    process_audio_task.delay(task_id, str(file_path), callback_url)

    log.info(f"Started diarization task {task_id} for file {audio_file.filename}")

    return TaskCreateResponse(
        task_id=task_id,
        status="queued",
        message="File uploaded successfully. Processing queued.",
        estimated_time_minutes=15
    )


@router.get("/diarize/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Check the status of a diarization task"""

    if not task_manager.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    status_data = task_manager.get_task_status(task_id)

    if status_data["status"] == "completed":
        status_data["download_url"] = f"/api/v1/diarize/download/{task_id}"

    return TaskStatus(**status_data)


@router.get("/diarize/download/{task_id}")
async def download_results(task_id: str):
    """Download diarization results as ZIP file"""

    if not task_manager.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    status = task_manager.get_task_status(task_id)

    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")

    zip_path = file_manager.get_result_zip(task_id)

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Results not found")

    return FileResponse(
        path=zip_path,
        filename=f"diarization_results_{task_id}.zip",
        media_type="application/zip"
    )


@router.get("/diarize/metadata/{task_id}", response_model=DetailedMetadata)
async def get_metadata(task_id: str):
    """Get detailed metadata without downloading ZIP"""

    if not task_manager.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    status = task_manager.get_task_status(task_id)

    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")

    metadata = file_manager.get_metadata(task_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")

    return DetailedMetadata(**metadata)
