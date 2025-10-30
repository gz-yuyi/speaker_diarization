import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # FastAPI
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=False)

    # Redis Connection Details
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_username: str = Field(default="")
    redis_password: str = Field(default="")
    redis_db_main: int = Field(default=0)
    redis_db_broker: int = Field(default=1)
    redis_db_backend: int = Field(default=2)

    # Storage
    storage_base_path: str = Field(default="./storage")
    max_file_size_mb: int = Field(default=500)
    supported_formats: str = Field(default="wav,mp3,flac,m4a,ogg")

    # Processing
    max_concurrent_tasks: int = Field(default=500)
    task_timeout_minutes: int = Field(default=1000)
    result_retention_days: int = Field(default=7)

    # Model Configuration
    model_name: str = Field(default="pyannote/speaker-diarization-community-1")
    model_path: str = Field(default="./models")  # Local model directory for offline loading

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/app.log")

    model_config = {"env_file": ".env"}

    @property
    def storage_base_path_obj(self) -> Path:
        return Path(self.storage_base_path)

    @property
    def log_file_obj(self) -> Path:
        return Path(self.log_file)

    @property
    def supported_formats_list(self) -> List[str]:
        return [fmt.strip() for fmt in self.supported_formats.split(",")]

    def build_redis_url(self, db: int) -> str:
        """Build Redis URL with authentication if username/password are provided"""
        if self.redis_username and self.redis_password:
            return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}:{self.redis_port}/{db}"
        elif self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{db}"

    @property
    def redis_url(self) -> str:
        """Get Redis URL for main database"""
        return self.build_redis_url(self.redis_db_main)

    @property
    def celery_broker_url(self) -> str:
        """Get Redis URL for Celery broker"""
        return self.build_redis_url(self.redis_db_broker)

    @property
    def celery_result_backend(self) -> str:
        """Get Redis URL for Celery result backend"""
        return self.build_redis_url(self.redis_db_backend)

    # Ensure directories exist
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create directories
        base_path = self.storage_base_path_obj
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / "uploads").mkdir(exist_ok=True)
        (base_path / "processed").mkdir(exist_ok=True)
        (base_path / "temp").mkdir(exist_ok=True)
        self.log_file_obj.parent.mkdir(parents=True, exist_ok=True)

        # Create model directory
        Path(self.model_path).mkdir(parents=True, exist_ok=True)

    @property
    def model_path_obj(self) -> Path:
        return Path(self.model_path)


settings = Settings()
