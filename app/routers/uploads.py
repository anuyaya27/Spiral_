from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_text
from app.db.session import get_db
from app.models.message import Message
from app.models.participant import Participant
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.upload import UploadCreateResponse, UploadRead
from app.schemas.llm_report import LLMReport
from app.services.analysis.runner import analyze_upload_and_store
from app.services.parsing import parse_chat_export
from app.services.storage import delete_file_if_exists, save_upload_file

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    file: UploadFile = File(...),
    platform: str | None = Form(default=None),
    timezone_name: str = Form("UTC"),
    label_names: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadCreateResponse:
    normalized_platform = (platform or _platform_from_filename(file.filename or "")).lower().strip()
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
    return UploadCreateResponse(upload_id=upload.id, message_count=len(parsed.messages))


def _platform_from_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".txt"):
        return "whatsapp"
    if lowered.endswith(".json"):
        return "generic"
    return ""


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


@router.post("/{upload_id}/analyze", response_model=LLMReport)
def analyze_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LLMReport:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    try:
        report_payload = analyze_upload_and_store(db, upload.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analysis failed. Please retry.") from exc
    return LLMReport.model_validate(report_payload)
