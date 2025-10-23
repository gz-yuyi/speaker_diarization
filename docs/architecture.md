# Code Directory Structure Design

## Project Structure

```
yuyi_speaker_diarization/
├── main.py                     # Entry point (CLI command using Click)
├── pyproject.toml             # uv package configuration
├── .env                       # Environment variables (local)
├── .env.example               # Environment variables template
├── README.md                  # Project documentation
├── docs/
│   ├── api.md                 # API documentation
│   └── architecture.md        # Architecture overview
├── src/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # API routes definitions
│   │   ├── models.py          # Pydantic models for request/response
│   │   └── middleware.py      # Custom middleware (logging, CORS)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management (dotenv)
│   │   ├── logger.py          # Loguru logger setup
│   │   └── exceptions.py      # Custom exceptions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_processor.py # Pyannote speaker diarization logic
│   │   ├── file_manager.py    # File storage and management
│   │   └── task_manager.py    # Task status management
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py      # Celery app configuration
│   │   └── tasks.py           # Celery tasks for audio processing
│   └── utils/
│       ├── __init__.py
│       ├── audio_utils.py     # Audio processing utilities
│       └── validators.py      # Input validation utilities
├── storage/                   # File storage (configurable via env)
│   ├── uploads/               # Uploaded audio files
│   ├── processed/             # Processed speaker segments
│   └── temp/                  # Temporary files
└── tests/                     # Test files
    ├── __init__.py
    ├── test_api.py
    ├── test_services.py
    └── test_workers.py
```

## Key Design Principles

1. **Flat Structure**: Keep nesting to minimum (max 3 levels deep)
2. **Clear Separation**: API, core logic, services, and workers are separate
3. **Single Responsibility**: Each module has a focused purpose
4. **Configurable**: All paths and settings via environment variables
5. **Scalable**: Easy to add new features or modify existing ones

## Entry Point Flow

`main.py` → Click CLI → FastAPI app → API routes → Celery tasks → Services

## Data Flow

1. Client uploads audio → FastAPI route → File storage → Celery task
2. Celery task → Audio processor → Pyannote → Segments by speaker
3. Results stored → Task status updated → Client notified/download

## Environment Variables

```env
# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Storage
STORAGE_BASE_PATH=./storage
MAX_FILE_SIZE_MB=500
SUPPORTED_FORMATS=wav,mp3,flac,m4a,ogg

# Processing
MAX_CONCURRENT_TASKS=10
TASK_TIMEOUT_MINUTES=60
RESULT_RETENTION_DAYS=7

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```