import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

ALLOWED = {
    "whatsapp": {".txt"},
    "imessage": {".json"},
    "generic": {".json"},
}

CONTENT_TYPES = {
    "whatsapp": {"text/plain", "application/octet-stream"},
    "imessage": {"application/json", "text/json", "application/octet-stream"},
    "generic": {"application/json", "text/json", "application/octet-stream"},
}


def ensure_upload_dir() -> Path:
    settings = get_settings()
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload_file(file: UploadFile, platform: str) -> str:
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED.get(platform, set()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file extension for {platform}")
    if file.content_type not in CONTENT_TYPES.get(platform, set()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid content type: {file.content_type}")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    upload_id = str(uuid.uuid4())
    root = ensure_upload_dir()
    final_path = root / f"{upload_id}{ext}"

    total = 0
    with final_path.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                handle.close()
                os.remove(final_path)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds max size")
            handle.write(chunk)
    await file.close()
    return str(final_path)


def delete_file_if_exists(path: str) -> None:
    p = Path(path)
    if p.exists():
        p.unlink(missing_ok=True)

