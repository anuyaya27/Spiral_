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
from app.models.report import Report
from app.models.upload import Upload
from app.services.parsing import parse_chat_export
from app.services.storage import delete_file_if_exists, save_upload_file
from app.services.analysis.runner import analyze_upload_and_store
from app.schemas.llm_report import LLMReport

router = APIRouter(prefix="/compat", tags=["compat"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def compat_upload(
    file: UploadFile = File(...),
    platform: str | None = Form(default=None),
    timezone_name: str = Form(default="UTC"),
    db: Session = Depends(get_db),
) -> dict:
    inferred_platform = (platform or _platform_from_filename(file.filename or "")).lower()
    if inferred_platform not in {"whatsapp", "imessage", "generic"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")

    saved_path = await save_upload_file(file, inferred_platform)
    try:
        parsed = parse_chat_export(saved_path, inferred_platform, timezone_name)
    except ValueError as exc:
        delete_file_if_exists(saved_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    retention_until = datetime.now(timezone.utc) + timedelta(days=get_settings().retention_days)
    upload = Upload(
        owner_id=None,
        platform=inferred_platform,
        timezone=timezone_name,
        status="parsed",
        file_path=saved_path,
        retention_until=retention_until,
        parsing_summary=parsed.summary,
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
    return {"upload_id": upload.id, "message_count": len(parsed.messages)}


@router.post("/uploads/{upload_id}/analyze", response_model=LLMReport)
def compat_analyze(upload_id: str, db: Session = Depends(get_db)) -> LLMReport:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    try:
        report_payload = analyze_upload_and_store(db, upload.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Analysis failed. Please retry.") from exc
    return LLMReport.model_validate(report_payload)


@router.get("/jobs/{job_id}")
def compat_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "progress": job.progress, "error": job.error}


@router.get("/reports/{upload_id}")
def compat_report(upload_id: str, db: Session = Depends(get_db)) -> dict:
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report.report_json


def _platform_from_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".txt"):
        return "whatsapp"
    if lowered.endswith(".json"):
        return "generic"
    return ""
