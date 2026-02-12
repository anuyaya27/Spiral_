from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_text
from app.db.session import get_db
from app.models.job import Job
from app.models.message import Message
from app.models.participant import Participant
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.upload import UploadCreateResponse, UploadRead
from app.services.parsing import parse_chat_export
from app.services.storage import delete_file_if_exists, save_upload_file
from app.workers.tasks import analyze_upload_job

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    file: UploadFile = File(...),
    platform: str = Form(...),
    timezone_name: str = Form("UTC"),
    label_names: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadCreateResponse:
    normalized_platform = platform.lower().strip()
    if normalized_platform not in {"whatsapp", "imessage", "generic"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")

    saved_path = await save_upload_file(file, normalized_platform)
    try:
        parsed = parse_chat_export(saved_path, normalized_platform, timezone_name)
    except ValueError as exc:
        delete_file_if_exists(saved_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    retention_until = datetime.now(timezone.utc) + timedelta(days=get_settings().retention_days)

    summary = {**parsed.summary}
    if label_names:
        summary["label_names"] = label_names

    upload = Upload(
        owner_id=current_user.id,
        platform=normalized_platform,
        timezone=timezone_name,
        status="parsed",
        file_path=saved_path,
        retention_until=retention_until,
        parsing_summary=summary,
    )
    db.add(upload)
    db.flush()

    participants_by_name: dict[str, Participant] = {}
    for name in parsed.participants:
        participant = Participant(upload_id=upload.id, display_name=name, normalized_id=name.lower().strip())
        db.add(participant)
        db.flush()
        participants_by_name[name] = participant

    for row in parsed.messages:
        sender = participants_by_name.get(row.sender)
        if sender is None:
            sender = Participant(upload_id=upload.id, display_name=row.sender, normalized_id=row.sender.lower().strip())
            db.add(sender)
            db.flush()
            participants_by_name[row.sender] = sender
        db.add(
            Message(
                upload_id=upload.id,
                ts=row.ts.astimezone(timezone.utc),
                sender_id=sender.id,
                encrypted_text=encrypt_text(row.text),
                metadata_json=row.metadata,
            )
        )
    db.commit()
    return UploadCreateResponse(upload_id=upload.id)


@router.get("/{upload_id}", response_model=UploadRead)
def get_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Upload:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    delete_file_if_exists(upload.file_path)
    db.delete(upload)
    db.commit()
    return None


@router.post("/{upload_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def analyze_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    job = Job(upload_id=upload.id, status="queued", progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)

    settings = get_settings()
    if settings.celery_task_always_eager:
        analyze_upload_job(job.id)
    else:
        task = analyze_upload_job.delay(job.id)
        job.task_id = task.id
        db.add(job)
        db.commit()
    return {"job_id": job.id}
