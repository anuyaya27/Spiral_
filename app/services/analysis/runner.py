from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_text
from app.models.job import Job
from app.models.message import Message
from app.models.participant import Participant
from app.models.report import Report
from app.models.upload import Upload
from app.services.llm import analyze_chat_with_llm


def analyze_upload_and_store(db: Session, upload_id: str, job: Job | None = None) -> dict:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id))
    if not upload:
        raise ValueError("Upload not found")

    participant_map = {
        p.id: p.display_name
        for p in db.scalars(select(Participant).where(Participant.upload_id == upload_id)).all()
    }
    rows = db.scalars(select(Message).where(Message.upload_id == upload_id).order_by(Message.ts.asc())).all()
    normalized = [
        {"ts": row.ts, "sender": participant_map.get(row.sender_id, "unknown"), "text": decrypt_text(row.encrypted_text)}
        for row in rows
    ]
    if not normalized:
        raise ValueError("No analyzable messages were found.")

    if job:
        job.status = "running"
        job.progress = 20
        db.add(job)
        db.commit()

    report_payload = analyze_chat_with_llm(normalized)

    existing_report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if existing_report:
        existing_report.report_json = report_payload
        existing_report.mixed_signal_index = report_payload["mixed_signal_index"]
        existing_report.confidence = report_payload["confidence"]
        existing_report.summary_text = report_payload["summary"]
        db.add(existing_report)
    else:
        db.add(
            Report(
                upload_id=upload_id,
                report_json=report_payload,
                mixed_signal_index=report_payload["mixed_signal_index"],
                confidence=report_payload["confidence"],
                summary_text=report_payload["summary"],
            )
        )

    settings = get_settings()
    upload.status = "analyzed"
    upload.retention_until = datetime.now(timezone.utc) + timedelta(days=settings.retention_days)
    db.add(upload)

    if job:
        job.status = "succeeded"
        job.progress = 100
        db.add(job)

    db.commit()
    return report_payload

