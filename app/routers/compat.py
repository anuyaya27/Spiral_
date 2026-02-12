from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_text, encrypt_text
from app.db.session import get_db
from app.models.excerpt import Excerpt
from app.models.job import Job
from app.models.message import Message
from app.models.participant import Participant
from app.models.report import Report
from app.models.upload import Upload
from app.services.parsing import parse_chat_export
from app.services.storage import delete_file_if_exists, save_upload_file
from app.workers.tasks import analyze_upload_job

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
    return {"upload_id": upload.id}


@router.post("/uploads/{upload_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def compat_analyze(upload_id: str, db: Session = Depends(get_db)) -> dict:
    upload = db.scalar(select(Upload).where(Upload.id == upload_id))
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
    report_json = _hydrate_moments_with_excerpt_text(db, upload_id, report.report_json)
    timeline, stats = _summarize_for_frontend(report_json)
    return {
        "mixed_signal_index": round(float(report.mixed_signal_index), 2),
        "confidence": round(float(report.confidence), 3),
        "timeline": timeline,
        "stats": stats,
        "full_report": report_json,
    }


def _platform_from_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".txt"):
        return "whatsapp"
    if lowered.endswith(".json"):
        return "generic"
    return ""


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


def _summarize_for_frontend(report_json: dict) -> tuple[list[dict], dict]:
    timeline: list[dict] = []
    moments = report_json.get("moments_of_ambiguity", [])
    for moment in moments:
        label = str(moment.get("label", "Mixed signal"))
        detectors = [str(d) for d in moment.get("detectors_triggered", [])]
        timeline_type = _type_from_detectors(detectors)
        for excerpt in moment.get("excerpts", [])[:2]:
            ts = excerpt.get("ts")
            timeline.append(
                {
                    "timestamp": ts,
                    "message": excerpt.get("text", ""),
                    "tags": _tags_from_label_and_detectors(label, detectors),
                    "type": timeline_type,
                }
            )
    timeline = [t for t in timeline if t.get("timestamp") and t.get("message")][:8]
    timeline.sort(key=lambda item: item["timestamp"])

    timeline_metrics = report_json.get("timeline_metrics", {})
    initiation_counts = timeline_metrics.get("initiation_counts", {})
    initiation_percent = _initiation_percent(initiation_counts)
    reply_ratio = _reply_delay_ratio(timeline_metrics.get("response_time_stats", {}))
    red_flags = _red_flag_count(report_json.get("detectors", []))

    return timeline, {
        "initiation_percent": initiation_percent,
        "reply_delay_ratio": reply_ratio,
        "red_flags": red_flags,
    }


def _type_from_detectors(detectors: list[str]) -> str:
    joined = " ".join(detectors)
    if any(token in joined for token in ("warm_cold", "contradiction", "unresolved")):
        return "mixed"
    if any(token in joined for token in ("boundary", "latency")):
        return "cool"
    return "warm"


def _tags_from_label_and_detectors(label: str, detectors: list[str]) -> list[str]:
    tags = [label.upper()[:26]]
    tags.extend(det.replace("_", " ").upper()[:24] for det in detectors[:2])
    return tags[:3]


def _initiation_percent(initiation_counts: dict) -> int:
    if not initiation_counts:
        return 0
    values = list(initiation_counts.values())
    total = sum(values)
    if total <= 0:
        return 0
    return int(round((max(values) / total) * 100))


def _reply_delay_ratio(response_time_stats: dict) -> float:
    averages = [float(item.get("avg_minutes", 0)) for item in response_time_stats.values() if item.get("avg_minutes")]
    if len(averages) < 2:
        return 1.0
    low = min(averages)
    high = max(averages)
    if low <= 0:
        return 1.0
    return round(high / low, 2)


def _red_flag_count(detectors: list[dict]) -> int:
    if not detectors:
        return 0
    return int(round(sum(float(det.get("score", 0)) for det in detectors) * 3))

