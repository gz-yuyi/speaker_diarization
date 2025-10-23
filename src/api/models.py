from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time_minutes: int


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    estimated_remaining_minutes: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    download_url: Optional[str] = None
    metadata: Optional[dict] = None


class SpeakerSegment(BaseModel):
    speaker_id: str
    segments_count: int
    total_speaking_time_seconds: float


class TaskMetadata(BaseModel):
    total_speakers: int
    total_duration_seconds: float
    speakers: List[SpeakerSegment]


class DetailedSegment(BaseModel):
    file_path: str
    start_time: float
    end_time: float
    duration_seconds: float
    confidence: float


class DetailedSpeaker(BaseModel):
    speaker_id: str
    segments: List[DetailedSegment]
    total_segments: int
    total_speaking_time_seconds: float
    average_confidence: float


class AudioInfo(BaseModel):
    original_filename: str
    duration_seconds: float
    sample_rate: int
    channels: int


class DiarizationResults(BaseModel):
    total_speakers: int
    total_segments: int
    processing_time_seconds: float


class DetailedMetadata(BaseModel):
    task_id: str
    audio_info: AudioInfo
    diarization_results: DiarizationResults
    speakers: List[DetailedSpeaker]