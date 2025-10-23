import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

import aiofiles

from src.core.config import settings
from src.core.logger import log


class FileManager:
    def __init__(self):
        self.uploads_dir = settings.storage_base_path_obj / "uploads"
        self.processed_dir = settings.storage_base_path_obj / "processed"
        self.temp_dir = settings.storage_base_path_obj / "temp"

    async def save_upload(self, task_id: str, audio_file) -> Path:
        """Save uploaded audio file"""
        task_upload_dir = self.uploads_dir / task_id
        task_upload_dir.mkdir(exist_ok=True)

        file_path = task_upload_dir / audio_file.filename

        async with aiofiles.open(file_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)

        log.info(f"Saved uploaded file to {file_path}")
        return file_path

    def get_upload_path(self, task_id: str) -> Path:
        """Get upload directory for task"""
        return self.uploads_dir / task_id

    def get_processed_path(self, task_id: str) -> Path:
        """Get processed directory for task"""
        processed_dir = self.processed_dir / task_id
        processed_dir.mkdir(exist_ok=True)
        return processed_dir

    def create_result_zip(self, task_id: str, speaker_segments: Dict[str, list], metadata: Dict[str, Any]) -> Path:
        """Create ZIP file with results"""
        processed_dir = self.get_processed_path(task_id)
        zip_path = processed_dir / f"results_{task_id}.zip"

        # Create speaker directories
        speaker_dirs = {}
        for speaker_id in speaker_segments.keys():
            speaker_dir = processed_dir / speaker_id
            speaker_dir.mkdir(exist_ok=True)
            speaker_dirs[speaker_id] = speaker_dir

        # Save metadata
        metadata_path = processed_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Create ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            zf.write(metadata_path, "metadata.json")

            # Add speaker directories
            for speaker_id, segments in speaker_segments.items():
                speaker_dir = speaker_dirs[speaker_id]
                for i, segment in enumerate(segments):
                    segment_path = speaker_dir / f"segment_{i+1:03d}.wav"
                    zf.write(segment_path, f"{speaker_id}/segment_{i+1:03d}.wav")

        log.info(f"Created result ZIP at {zip_path}")
        return zip_path

    def get_result_zip(self, task_id: str) -> Path:
        """Get result ZIP path"""
        return self.processed_dir / task_id / f"results_{task_id}.zip"

    def get_metadata(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for task"""
        metadata_path = self.processed_dir / task_id / "metadata.json"
        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r') as f:
            return json.load(f)

    def cleanup_task(self, task_id: str):
        """Clean up task files"""
        upload_dir = self.uploads_dir / task_id
        processed_dir = self.processed_dir / task_id

        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            log.info(f"Cleaned up upload directory: {upload_dir}")

        if processed_dir.exists():
            shutil.rmtree(processed_dir)
            log.info(f"Cleaned up processed directory: {processed_dir}")

    def cleanup_old_tasks(self, days: int = None):
        """Clean up old tasks"""
        if days is None:
            days = settings.result_retention_days

        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

        for task_dir in self.processed_dir.iterdir():
            if task_dir.is_dir() and task_dir.stat().st_mtime < cutoff_time:
                self.cleanup_task(task_dir.name)
                log.info(f"Cleaned up old task: {task_dir.name}")