# Speaker Diarization API Documentation

## Overview

This API provides speaker diarization capabilities using pyannote to separate audio files by speaker. Given a long audio file with multiple speakers, the service identifies individual speakers and creates separate audio segments for each person.

## Features

- Supports long audio files (up to 1 hour)
- Detects multiple speakers in conversation
- Separates audio by speaker into individual segments
- Asynchronous task processing
- Returns metadata with timestamps and file paths

## API Endpoints

### 1. Upload Audio and Start Diarization Task

**POST** `/api/v1/diarize/upload`

Upload an audio file to start the diarization process.

#### Request

- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `audio_file`: (required) Audio file to process
  - `callback_url`: (optional) URL to notify when task is complete

#### Response

```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "File uploaded successfully. Processing started.",
  "estimated_time_minutes": 15
}
```

#### Example Request

```bash
curl -X POST \
  http://localhost:8000/api/v1/diarize/upload \
  -H 'Content-Type: multipart/form-data' \
  -F 'audio_file=@/path/to/your/audio.wav' \
  -F 'callback_url=https://your-app.com/callback'
```

### 2. Check Task Status

**GET** `/api/v1/diarize/status/{task_id}`

Check the status of a diarization task.

#### Parameters

- `task_id`: UUID of the task to check

#### Response

**Pending/Processing Status**:
```json
{
  "task_id": "uuid-string",
  "status": "processing",
  "progress": 45,
  "estimated_remaining_minutes": 8,
  "message": "Processing audio file..."
}
```

**Completed Status**:
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "progress": 100,
  "download_url": "/api/v1/diarize/download/{task_id}",
  "metadata": {
    "total_speakers": 3,
    "total_duration_seconds": 3600,
    "speakers": [
      {
        "speaker_id": "speaker_0",
        "segments_count": 15,
        "total_speaking_time_seconds": 1200
      },
      {
        "speaker_id": "speaker_1", 
        "segments_count": 12,
        "total_speaking_time_seconds": 1500
      },
      {
        "speaker_id": "speaker_2",
        "segments_count": 8,
        "total_speaking_time_seconds": 900
      }
    ]
  }
}
```

**Failed Status**:
```json
{
  "task_id": "uuid-string",
  "status": "failed",
  "error": "Audio format not supported",
  "error_code": "INVALID_AUDIO_FORMAT"
}
```

### 3. Download Results

**GET** `/api/v1/diarize/download/{task_id}`

Download the diarization results as a ZIP file containing speaker folders and metadata.

#### Parameters

- `task_id`: UUID of the completed task

#### Response

Returns a ZIP file containing:
- `speaker_0/` - Folder with audio segments for speaker 0
- `speaker_1/` - Folder with audio segments for speaker 1
- `speaker_2/` - Folder with audio segments for speaker 2
- `metadata.json` - Detailed metadata file

### 4. Get Detailed Metadata

**GET** `/api/v1/diarize/metadata/{task_id}`

Get detailed metadata without downloading the ZIP file.

#### Parameters

- `task_id`: UUID of the completed task

#### Response

```json
{
  "task_id": "uuid-string",
  "audio_info": {
    "original_filename": "conversation.wav",
    "duration_seconds": 3600,
    "sample_rate": 16000,
    "channels": 1
  },
  "diarization_results": {
    "total_speakers": 3,
    "total_segments": 35,
    "processing_time_seconds": 180
  },
  "speakers": [
    {
      "speaker_id": "speaker_0",
      "segments": [
        {
          "file_path": "speaker_0/segment_001.wav",
          "start_time": 0.5,
          "end_time": 12.3,
          "duration_seconds": 11.8,
          "confidence": 0.95
        },
        {
          "file_path": "speaker_0/segment_002.wav", 
          "start_time": 45.2,
          "end_time": 67.8,
          "duration_seconds": 22.6,
          "confidence": 0.92
        }
      ],
      "total_segments": 15,
      "total_speaking_time_seconds": 1200,
      "average_confidence": 0.94
    }
  ]
}
```

## Supported Audio Formats

- WAV (.wav)
- MP3 (.mp3)
- FLAC (.flac)
- M4A (.m4a)
- OGG (.ogg)

## File Size Limits

- Maximum file size: 500MB
- Recommended duration: Up to 1 hour
- Minimum duration: 30 seconds

## Error Codes

| Error Code | Description |
|------------|-------------|
| INVALID_AUDIO_FORMAT | Audio format not supported |
| FILE_TOO_LARGE | File exceeds size limit |
| PROCESSING_FAILED | Diarization processing failed |
| TASK_NOT_FOUND | Task ID not found |
| TASK_EXPIRED | Task results have expired (7 days) |

## Usage Flow

1. **Upload**: Send audio file to `/api/v1/diarize/upload`
2. **Receive Task ID**: Get unique task ID for tracking
3. **Check Status**: Poll `/api/v1/diarize/status/{task_id}` periodically
4. **Download Results**: When status is "completed", download from `/api/v1/diarize/download/{task_id}`

## Rate Limiting

- Maximum 10 concurrent tasks per user
- Maximum 100 uploads per hour
- Results are stored for 7 days

## Webhook Callbacks (Optional)

If you provide a `callback_url` when uploading, the system will send a POST request when processing is complete:

```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "download_url": "/api/v1/diarize/download/uuid-string",
  "metadata": { ... }
}
```

## Python SDK Example

```python
import requests
import time

# Upload audio file
with open('conversation.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/diarize/upload',
        files={'audio_file': f}
    )

task_id = response.json()['task_id']

# Poll for completion
while True:
    status_response = requests.get(f'http://localhost:8000/api/v1/diarize/status/{task_id}')
    status = status_response.json()['status']
    
    if status == 'completed':
        break
    elif status == 'failed':
        print("Processing failed!")
        break
    
    time.sleep(10)  # Wait 10 seconds before checking again

# Download results
download_response = requests.get(f'http://localhost:8000/api/v1/diarize/download/{task_id}')
with open('results.zip', 'wb') as f:
    f.write(download_response.content)
```