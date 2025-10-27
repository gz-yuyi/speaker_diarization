import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable

import torch
import torchaudio
from pyannote.audio import Pipeline
from pyannote.core import Annotation, Segment

from src.services.file_manager import FileManager
from src.core.config import settings
from src.core.logger import log

file_manager = FileManager()


class AudioProcessor:
    def __init__(self):
        self.pipeline = None
        self._load_pipeline()

    def _load_pipeline(self):
        """Load Pyannote pipeline - try offline first, then online"""
        # Load from local model directory first (offline mode)
        local_model_path = settings.model_path_obj / settings.model_name.replace("/", "--")

        if local_model_path.exists():
            log.info(f"Loading Pyannote pipeline from local path: {local_model_path}")
            self.pipeline = Pipeline.from_pretrained(str(local_model_path))
        else:
            log.info(f"Local model not found at {local_model_path}, trying to load from Hugging Face...")
            log.warning("Note: This requires internet connection and Hugging Face access token")
            log.warning("For offline usage, run: python main.py download-model --auth-token YOUR_TOKEN")

            # Load from Hugging Face (will fail without auth token)
            self.pipeline = Pipeline.from_pretrained(settings.model_name)

        # Move pipeline to GPU if available
        if torch.cuda.is_available():
            self.pipeline.to(torch.device("cuda"))
            log.info("Pyannote pipeline loaded on GPU")
        else:
            log.info("Pyannote pipeline loaded on CPU")

    def process_audio(
        self,
        audio_path: Path,
        task_id: str,
        progress_callback: Callable[[int, str], None] = None
    ) -> Tuple[Dict[str, List[Path]], Dict[str, Any]]:
        """Process audio file and return speaker segments and metadata"""

        if progress_callback:
            progress_callback(30, "Analyzing audio...")

        # Load audio
        waveform, sample_rate = torchaudio.load(str(audio_path))

        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        audio_info = {
            "original_filename": audio_path.name,
            "duration_seconds": float(waveform.shape[1] / sample_rate),
            "sample_rate": sample_rate,
            "channels": 1
        }

        if progress_callback:
            progress_callback(50, "Running speaker diarization...")

        # Run diarization
        diarization_result = self.pipeline({
            "waveform": waveform,
            "sample_rate": sample_rate
        })

        # Get diarization results from newer Pyannote versions
        diarization = diarization_result.speaker_diarization

        if progress_callback:
            progress_callback(70, "Processing speaker segments...")

        # Process results
        speaker_segments = {}
        detailed_speakers = []

        # Group segments by speaker
        speaker_segments_raw = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speaker_segments_raw:
                speaker_segments_raw[speaker] = []
            speaker_segments_raw[speaker].append({
                "start": float(turn.start),
                "end": float(turn.end),
                "duration": float(turn.duration)
            })

        # Create audio segments for each speaker
        processed_dir = file_manager.get_processed_path(task_id)
        total_segments = 0
        processing_time = 0.0

        for speaker_id, segments in speaker_segments_raw.items():
            speaker_dir = processed_dir / speaker_id
            speaker_dir.mkdir(exist_ok=True)

            segment_files = []
            detailed_segments = []
            speaking_time = 0.0
            confidences = []

            for i, segment in enumerate(segments):
                # Extract audio segment
                start_sample = int(segment["start"] * sample_rate)
                end_sample = int(segment["end"] * sample_rate)

                segment_waveform = waveform[:, start_sample:end_sample]

                # Save segment
                segment_filename = f"segment_{i+1:03d}.wav"
                segment_path = speaker_dir / segment_filename
                torchaudio.save(str(segment_path), segment_waveform, sample_rate)

                segment_files.append(segment_path)
                total_segments += 1
                speaking_time += segment["duration"]

                # Calculate confidence (simplified - in real implementation this would come from diarization)
                confidence = min(0.95, 0.7 + (segment["duration"] / 10.0))
                confidences.append(confidence)

                detailed_segments.append({
                    "file_path": f"{speaker_id}/{segment_filename}",
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "duration_seconds": segment["duration"],
                    "confidence": confidence
                })

            speaker_segments[speaker_id] = segment_files

            detailed_speakers.append({
                "speaker_id": speaker_id,
                "segments": detailed_segments,
                "total_segments": len(segments),
                "total_speaking_time_seconds": speaking_time,
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0
            })

        # Create metadata
        metadata = {
            "task_id": task_id,
            "audio_info": audio_info,
            "diarization_results": {
                "total_speakers": len(speaker_segments),
                "total_segments": total_segments,
                "processing_time_seconds": processing_time
            },
            "speakers": detailed_speakers
        }

        if progress_callback:
            progress_callback(85, "Finalizing results...")

        log.info(f"Processed audio for task {task_id}: {len(speaker_segments)} speakers, {total_segments} segments")

        return speaker_segments, metadata

    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return settings.supported_formats_list
