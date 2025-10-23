import redis
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.config import settings
from src.core.logger import log


class TaskManager:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)

    def create_task(self, task_id: str, initial_data: Dict[str, Any] = None):
        """Create a new task"""
        task_data = {
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Task created"
        }

        if initial_data:
            task_data.update(initial_data)

        self.redis_client.hset(f"task:{task_id}", mapping=task_data)
        log.info(f"Created task {task_id}")

    def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        return self.redis_client.exists(f"task:{task_id}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        task_data = self.redis_client.hgetall(f"task:{task_id}")
        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        # Convert bytes to strings
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}

    def update_task_status(self, task_id: str, status: str, progress: int = None, message: str = None):
        """Update task status"""
        update_data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }

        if progress is not None:
            update_data["progress"] = str(progress)

        if message:
            update_data["message"] = message

        self.redis_client.hset(f"task:{task_id}", mapping=update_data)
        log.info(f"Updated task {task_id} status to {status}")

    def set_task_progress(self, task_id: str, progress: int, message: str = None):
        """Set task progress"""
        update_data = {
            "progress": str(progress),
            "updated_at": datetime.now().isoformat()
        }

        if message:
            update_data["message"] = message

        self.redis_client.hset(f"task:{task_id}", mapping=update_data)

    def set_task_error(self, task_id: str, error: str, error_code: str = None):
        """Set task error"""
        update_data = {
            "status": "failed",
            "error": error,
            "updated_at": datetime.now().isoformat()
        }

        if error_code:
            update_data["error_code"] = error_code

        self.redis_client.hset(f"task:{task_id}", mapping=update_data)
        log.error(f"Task {task_id} failed: {error}")

    def set_task_completed(self, task_id: str, metadata: Dict[str, Any] = None):
        """Mark task as completed"""
        update_data = {
            "status": "completed",
            "progress": "100",
            "message": "Task completed successfully",
            "completed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self.redis_client.hset(f"task:{task_id}", mapping=update_data)

        if metadata:
            # Store metadata separately
            metadata_key = f"task_metadata:{task_id}"
            self.redis_client.set(metadata_key, str(metadata))

        log.info(f"Task {task_id} completed successfully")

    def get_active_task_count(self) -> int:
        """Get number of active (pending/processing) tasks"""
        count = 0
        for key in self.redis_client.scan_iter(match="task:*"):
            status = self.redis_client.hget(key, "status")
            if status and status.decode('utf-8') in ["pending", "processing"]:
                count += 1
        return count

    def can_start_new_task(self) -> bool:
        """Check if new task can be started based on concurrent limit"""
        return self.get_active_task_count() < settings.max_concurrent_tasks

    def delete_task(self, task_id: str):
        """Delete task"""
        self.redis_client.delete(f"task:{task_id}")
        self.redis_client.delete(f"task_metadata:{task_id}")
        log.info(f"Deleted task {task_id}")