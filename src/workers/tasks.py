import httpx
from celery import Task
from pathlib import Path

from src.workers.celery_app import celery_app
from src.services.task_manager import TaskManager
from src.services.file_manager import FileManager
from src.services.audio_processor import AudioProcessor
from src.core.config import settings
from src.core.logger import log

task_manager = TaskManager()
file_manager = FileManager()
_audio_processor: AudioProcessor | None = None


def get_audio_processor() -> AudioProcessor:
    """Instantiate AudioProcessor lazily per worker process."""

    global _audio_processor

    if _audio_processor is None:
        log.info("Initializing AudioProcessor in worker process")
        _audio_processor = AudioProcessor()

    return _audio_processor


class DiarizationTask(Task):
    """Custom task class for diarization"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        task_manager.set_task_error(
            task_id,
            str(exc),
            "PROCESSING_FAILED"
        )
        log.error(f"Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        log.info(f"Task {task_id} completed successfully")


@celery_app.task(bind=True, base=DiarizationTask, name="process_audio_task")
def process_audio_task(self, task_id: str, audio_file_path: str, callback_url: str = None):
    """Process audio file for speaker diarization"""

    try:
        # Ensure task record exists
        if not task_manager.task_exists(task_id):
            task_manager.create_task(task_id)

        # Check if we can start new task
        if not task_manager.can_start_new_task():
            task_manager.set_task_error(
                task_id,
                "Too many concurrent tasks. Please try again later.",
                "QUEUE_FULL"
            )
            return

        # Check concurrent task limit
        if not task_manager.can_start_new_task():
            task_manager.update_task_status(
                task_id,
                "queued",
                message="Task queued. Waiting for available slot."
            )
            # Wait for available slot (simple implementation)
            import time
            while not task_manager.can_start_new_task():
                time.sleep(5)

        # Start processing
        task_manager.update_task_status(task_id, "processing", progress=10, message="Starting audio processing...")

        audio_path = Path(audio_file_path)
        log.info(f"Loading audio from {audio_path} for task {task_id}")

        # Process audio
        task_manager.set_task_progress(task_id, 20, "Loading audio file...")

        log.info(f"Starting diarization pipeline for task {task_id}")

        audio_processor = get_audio_processor()

        speaker_segments, metadata = audio_processor.process_audio(
            audio_path,
            task_id,
            progress_callback=lambda progress, message: task_manager.set_task_progress(task_id, progress, message)
        )

        log.info(f"Diarization pipeline completed for task {task_id}")

        # Create result ZIP
        task_manager.set_task_progress(task_id, 90, "Creating result package...")
        file_manager.create_result_zip(task_id, speaker_segments, metadata)

        # Mark task as completed
        task_manager.set_task_completed(task_id, metadata)

        # Send callback if provided
        if callback_url:
            try:
                with httpx.Client() as client:
                    callback_data = {
                        "task_id": task_id,
                        "status": "completed",
                        "download_url": f"/api/v1/diarize/download/{task_id}",
                        "metadata": metadata
                    }
                    client.post(callback_url, json=callback_data)
                    log.info(f"Sent callback to {callback_url}")
            except Exception as e:
                log.warning(f"Failed to send callback: {e}")

        log.info(f"Successfully processed task {task_id}")
        return {"status": "completed", "task_id": task_id}

    except Exception as e:
        log.error(f"Error processing task {task_id}: {e}")
        raise


@celery_app.task(name="cleanup_old_tasks")
def cleanup_old_tasks():
    """Clean up old tasks and files"""
    log.info("Starting cleanup of old tasks...")
    file_manager.cleanup_old_tasks()
    log.info("Cleanup completed")
