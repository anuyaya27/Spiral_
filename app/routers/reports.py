from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.report import Report
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.llm_report import LLMReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{upload_id}", response_model=LLMReport)
def get_report(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> LLMReport:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return LLMReport.model_validate(report.report_json)


@router.get("/{upload_id}/highlights")
def get_highlights(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id, Upload.owner_id == current_user.id))
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    report = db.scalar(select(Report).where(Report.upload_id == upload_id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    payload = LLMReport.model_validate(report.report_json).model_dump(mode="json")
    return {"upload_id": upload_id, "highlights": payload.get("timeline", [])}


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
    payload = LLMReport.model_validate(report.report_json).model_dump(mode="json")
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "upload_id": upload_id,
        "mixed_signal_index": report.mixed_signal_index,
        "confidence": report.confidence,
        "summary_text": report.summary_text,
        "report": payload,
    }
    return JSONResponse(payload, headers={"Content-Disposition": f"attachment; filename=report-{upload_id}.json"})
