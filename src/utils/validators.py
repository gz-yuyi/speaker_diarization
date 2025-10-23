import re
from typing import Optional
from pathlib import Path


def validate_task_id(task_id: str) -> bool:
    """Validate task ID format (UUID)"""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(task_id))


def validate_filename(filename: str) -> bool:
    """Validate filename for security"""
    if not filename:
        return False

    # Check for path traversal attempts
    if ".." in filename or "/" in filename or "\\" in filename:
        return False

    # Check for dangerous characters
    dangerous_chars = ["<", ">", ":", "\"", "|", "?", "*"]
    if any(char in filename for char in dangerous_chars):
        return False

    return True


def validate_audio_format(filename: str, supported_formats: list) -> bool:
    """Validate audio file format"""
    if not filename:
        return False

    extension = Path(filename).suffix.lower().lstrip('.')
    return extension in [fmt.lower() for fmt in supported_formats]