from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_text
from app.db.session import get_db
from app.models.excerpt import Excerpt
from app.models.report import Report
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.report import ReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{upload_id}", response_model=ReportRead)
def get_report(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ReportRead:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    hydrated = _hydrate_moments_with_excerpt_text(db, upload_id, report.report_json)
    return ReportRead(
        upload_id=report.upload_id,
        created_at=report.created_at,
        mixed_signal_index=report.mixed_signal_index,
        confidence=report.confidence,
        summary_text=report.summary_text,
        report_json=hydrated,
    )


@router.get("/{upload_id}/highlights")
def get_highlights(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    hydrated = _hydrate_moments_with_excerpt_text(db, upload_id, report.report_json)
    moments = hydrated.get("moments_of_ambiguity", [])
    return {"upload_id": upload_id, "highlights": moments}


@router.get("/{upload_id}/download")
def download_report(
    upload_id: str,
    format: str = Query("json", pattern="^(json|pdf)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if format == "pdf":
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="PDF export is not implemented yet")
    hydrated = _hydrate_moments_with_excerpt_text(db, upload_id, report.report_json)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "upload_id": upload_id,
        "mixed_signal_index": report.mixed_signal_index,
        "confidence": report.confidence,
        "summary_text": report.summary_text,
        "report": hydrated,
    }
    return JSONResponse(payload, headers={"Content-Disposition": f"attachment; filename=report-{upload_id}.json"})


def _hydrate_moments_with_excerpt_text(db: Session, upload_id: str, report_json: dict) -> dict:
    import copy

    payload = copy.deepcopy(report_json)
    rows = db.scalars(select(Excerpt).where(Excerpt.upload_id == upload_id)).all()
    by_message_id = {row.message_id: row for row in rows}
    for moment in payload.get("moments_of_ambiguity", []):
        for excerpt in moment.get("excerpts", []):
            row = by_message_id.get(excerpt.get("message_id"))
            excerpt["text"] = decrypt_text(row.encrypted_excerpt) if row else ""
    return payload
