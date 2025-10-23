import mimetypes
from pathlib import Path
from typing import Optional, Tuple

import torchaudio


def get_audio_info(file_path: Path) -> Tuple[int, int, float]:
    """Get audio file info: sample_rate, channels, duration"""
    try:
        waveform, sample_rate = torchaudio.load(str(file_path))
        channels = waveform.shape[0]
        duration = waveform.shape[1] / sample_rate
        return sample_rate, channels, duration
    except Exception as e:
        raise ValueError(f"Failed to read audio file {file_path}: {e}")


def is_audio_file(file_path: Path) -> bool:
    """Check if file is a supported audio format"""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type and mime_type.startswith('audio/'):
        return True
    return False


def validate_audio_file(file_path: Path, max_size_mb: int = 500) -> bool:
    """Validate audio file"""
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if not is_audio_file(file_path):
        raise ValueError(f"Not a valid audio file: {file_path}")

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"File too large: {file_size_mb:.1f}MB > {max_size_mb}MB")

    return True


def convert_to_mono_if_needed(file_path: Path, output_path: Path) -> Path:
    """Convert audio to mono if it has multiple channels"""
    try:
        waveform, sample_rate = torchaudio.load(str(file_path))

        if waveform.shape[0] > 1:
            # Convert to mono
            mono_waveform = torch.mean(waveform, dim=0, keepdim=True)
            torchaudio.save(str(output_path), mono_waveform, sample_rate)
            return output_path
        else:
            # Already mono
            return file_path

    except Exception as e:
        raise ValueError(f"Failed to convert audio to mono: {e}")