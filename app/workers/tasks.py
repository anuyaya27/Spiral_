import copy
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.excerpt import Excerpt
from app.models.job import Job
from app.models.report import Report
from app.models.upload import Upload
from app.services.analysis.pipeline import run_analysis
from app.services.retention import run_retention_cleanup
from app.core.config import get_settings
from app.core.security import encrypt_text

logger = logging.getLogger(__name__)
settings = get_settings()


def analyze_upload_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if not job:
            return
        upload = db.scalar(select(Upload).where(Upload.id == job.upload_id))
        if not upload:
            job.status = "failed"
            job.error = "Upload not found"
            db.add(job)
            db.commit()
            return

        job.status = "running"
        job.progress = 10
        db.add(job)
        db.commit()

        report_payload = run_analysis(db, upload.id)
        report_for_storage = copy.deepcopy(report_payload)
        job.progress = 85

        existing_report = db.scalar(select(Report).where(Report.upload_id == upload.id))
        if existing_report:
            existing_report.report_json = report_for_storage
            existing_report.mixed_signal_index = report_for_storage["mixed_signal_index"]
            existing_report.confidence = report_for_storage["confidence"]
            existing_report.summary_text = report_for_storage["summary_text"]
            db.add(existing_report)
        else:
            db.add(
                Report(
                    upload_id=upload.id,
                    report_json=report_for_storage,
                    mixed_signal_index=report_for_storage["mixed_signal_index"],
                    confidence=report_for_storage["confidence"],
                    summary_text=report_for_storage["summary_text"],
                )
            )

        db.query(Excerpt).filter(Excerpt.upload_id == upload.id).delete()
        for moment_idx, moment in enumerate(report_payload.get("moments_of_ambiguity", [])):
            storage_moment = report_for_storage["moments_of_ambiguity"][moment_idx]
            for excerpt_idx, excerpt in enumerate(moment.get("excerpts", [])):
                db.add(
                    Excerpt(
                        upload_id=upload.id,
                        message_id=excerpt["message_id"],
                        encrypted_excerpt=encrypt_text(excerpt.get("raw_text", "")),
                        purpose="ambiguity_highlight",
                    )
                )
                storage_moment["excerpts"][excerpt_idx].pop("raw_text", None)

        upload.status = "analyzed"
        upload.retention_until = datetime.now(timezone.utc) + timedelta(days=settings.retention_days)
        job.status = "succeeded"
        job.progress = 100
        db.add_all([upload, job])
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("analysis_job_failed", extra={"job_id": job_id, "error": str(exc)})
        failed = db.scalar(select(Job).where(Job.id == job_id))
        if failed:
            failed.status = "failed"
            failed.error = str(exc)
            failed.progress = failed.progress or 0
            db.add(failed)
            db.commit()
    finally:
        db.close()


def retention_cleanup_job() -> int:
    db = SessionLocal()
    try:
        return run_retention_cleanup(db)
    finally:
        db.close()
