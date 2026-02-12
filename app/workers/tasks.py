import logging

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.job import Job
from app.services.analysis.runner import analyze_upload_and_store
from app.services.retention import run_retention_cleanup

logger = logging.getLogger(__name__)


def analyze_upload_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if not job:
            return
        analyze_upload_and_store(db, job.upload_id, job=job)
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
