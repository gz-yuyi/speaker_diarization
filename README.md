# Speaker Diarization API

FastAPI-based speaker diarization service using pyannote to separate audio files by speaker with asynchronous task processing.

## Quick Start

### Prerequisites

- Python 3.12+
- Redis server
- uv package manager

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration if needed
```

3. Initialize storage directories:
```bash
uv run python main.py init-storage
```

### Running the Application

1. **Start Redis server** (required for Celery):
```bash
redis-server
```

2. **Start the Celery worker** (in a separate terminal):
```bash
uv run python main.py worker --concurrency 4
```

3. **Start the API server** (in another terminal):
```bash
uv run python main.py start --host 0.0.0.0 --port 8000
```

### CLI Commands

```bash
# Start API server
uv run python main.py start

# Start Celery worker
uv run python main.py worker

# Check system status
uv run python main.py status

# Initialize storage directories
uv run python main.py init-storage

# Check external services connectivity
uv run python main.py check-external-service
```

### API Usage

Upload audio file and check status:

```bash
# Upload audio file
curl -X POST \
  http://localhost:8000/api/v1/diarize/upload \
  -H 'Content-Type: multipart/form-data' \
  -F 'audio_file=@conversation.wav'

# Check task status (replace {task_id} with actual ID)
curl http://localhost:8000/api/v1/diarize/status/{task_id}

# Download results when completed
curl -O http://localhost:8000/api/v1/diarize/download/{task_id}
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed.

### Redis Configuration

The application requires Redis for caching and Celery task queue. Configure Redis connection using the following environment variables:

```bash
# Redis/Celery Connection Details
REDIS_HOST=localhost              # Redis server host
REDIS_PORT=6379                   # Redis server port
REDIS_USERNAME=                   # Redis username (leave empty if not required)
REDIS_PASSWORD=your_password_here # Redis password (leave empty if no password)
REDIS_DB_MAIN=0                   # Database for main Redis operations
REDIS_DB_BROKER=1                 # Database for Celery message broker
REDIS_DB_BACKEND=2                # Database for Celery result storage
```

**Authentication Options:**
- **No authentication**: Leave both `REDIS_USERNAME` and `REDIS_PASSWORD` empty
- **Password only**: Set only `REDIS_PASSWORD` (traditional Redis auth)
- **Username + Password**: Set both `REDIS_USERNAME` and `REDIS_PASSWORD` (Redis ACL/Alibaba Cloud Redis)

### Testing Redis Connectivity

Use the built-in command to verify Redis connectivity:

```bash
# Check external services connectivity
uv run python main.py check-external-service
```

This command will test connections to all Redis instances and report their status, masking passwords in the output for security.

### Model Configuration (Offline Usage)

The application uses Pyannote's speaker diarization model which requires a Hugging Face access token. For complete offline operation, download the model first:

```bash
# Download model for offline usage
uv run python main.py download-model --auth-token YOUR_HUGGING_FACE_TOKEN

# Custom model name and output directory
uv run python main.py download-model --auth-token YOUR_TOKEN --model-name pyannote/speaker-diarization-3.1 --output-dir ./models
```

**Model Configuration Environment Variables:**
```bash
MODEL_NAME=pyannote/speaker-diarization-3.1  # Model identifier
MODEL_PATH=./models                          # Local model storage directory
```

**Setup Steps:**
1. Get a Hugging Face access token from https://huggingface.co/settings/tokens
2. Accept the user agreement at: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Download the model: `uv run python main.py download-model --auth-token YOUR_TOKEN`
4. The model will be saved to `./models/pyannote--speaker-diarization-3.1/`
5. Run the application completely offline

**Note:** The first time you run the download command, ensure you have:
- Valid Hugging Face access token
- Accepted the model's user agreement
- Stable internet connection (download size: ~1GB)

## Documentation

- [API Documentation](docs/api.md) - Complete API reference
- [Architecture Overview](docs/architecture.md) - System design and structure
- [Implementation Plan](docs/implementation_plan.md) - Development roadmap

## API Docs

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`