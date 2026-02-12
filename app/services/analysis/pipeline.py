from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_text
from app.models.message import Message
from app.models.participant import Participant
from app.services.analysis.detectors import run_detectors
from app.services.analysis.features import extract_message_features
from app.services.analysis.scoring import compute_confidence, compute_mixed_signal_index


def run_analysis(db: Session, upload_id: str) -> dict:
    participant_map = {
        p.id: p.display_name
        for p in db.scalars(select(Participant).where(Participant.upload_id == upload_id)).all()
    }
    message_rows = db.scalars(select(Message).where(Message.upload_id == upload_id).order_by(Message.ts.asc())).all()
    messages = [
        {
            "id": m.id,
            "ts": m.ts.astimezone(timezone.utc),
            "sender_id": m.sender_id,
            "sender_name": participant_map.get(m.sender_id, "unknown"),
            "text": decrypt_text(m.encrypted_text),
        }
        for m in message_rows
    ]
    if not messages:
        return {
            "timeline_metrics": {},
            "detectors": [],
            "mixed_signal_index": 0.0,
            "confidence": 0.0,
            "sub_scores": {},
            "moments_of_ambiguity": [],
            "summary_text": "No analyzable messages were found.",
        }

    features = extract_message_features(messages)
    timeline_metrics = _timeline_metrics(features)
    detector_results = run_detectors(features)
    days = (messages[-1]["ts"].date() - messages[0]["ts"].date()).days + 1
    confidence = compute_confidence(len(messages), max(days, 1), detector_results)
    mixed_signal_index, sub_scores = compute_mixed_signal_index(detector_results, confidence)
    moments = _moments_of_ambiguity(features, detector_results)
    summary_text = _summary_text(mixed_signal_index, confidence, detector_results)

    return {
        "timeline_metrics": timeline_metrics,
        "detectors": [
            {"name": d.detector, "score": round(d.score, 3), "explanation": d.explanation, "evidence_ids": d.evidence_ids}
            for d in detector_results
        ],
        "mixed_signal_index": mixed_signal_index,
        "confidence": confidence,
        "sub_scores": sub_scores,
        "moments_of_ambiguity": moments,
        "summary_text": summary_text,
    }


def _timeline_metrics(features: list[dict]) -> dict:
    from app.services.analysis.features import build_timeline_metrics

    metrics = build_timeline_metrics(features)
    return {
        "messages_per_day": dict(metrics.get("messages_per_day", {})),
        "messages_per_week": dict(metrics.get("messages_per_week", {})),
        "response_time_stats": metrics.get("response_time_stats", {}),
        "initiation_counts": dict(metrics.get("initiation_counts", {})),
        "streaks": metrics.get("streaks", {}),
        "engagement_shifts": metrics.get("engagement_shifts", []),
    }


def _moments_of_ambiguity(features: list[dict], detector_results: list) -> list[dict]:
    settings = get_settings()
    by_id = {row["id"]: row for row in features}
    windows: list[dict] = []
    for detector in detector_results:
        if not detector.evidence_ids:
            continue
        evidence_msgs = [by_id[mid] for mid in detector.evidence_ids if mid in by_id]
        if not evidence_msgs:
            continue
        evidence_msgs.sort(key=lambda x: x["ts"])
        start = evidence_msgs[0]["ts"] - timedelta(hours=2)
        end = evidence_msgs[-1]["ts"] + timedelta(hours=2)
        windows.append(
            {
                "label": _label_for_detector(detector.detector),
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
                "detectors_triggered": [detector.detector],
                "evidence_ids": [m["id"] for m in evidence_msgs[:4]],
                "excerpts": [
                    {"message_id": m["id"], "sender": m["sender_name"], "ts": m["ts"].isoformat(), "raw_text": m["text"][:220]}
                    for m in evidence_msgs[:4]
                ],
            }
        )
    windows.sort(key=lambda w: len(w["evidence_ids"]), reverse=True)
    return windows[: settings.ambiguity_windows_top_n]


def _label_for_detector(detector: str) -> str:
    labels = {
        "initiation_imbalance": "Initiation mismatch",
        "response_latency_asymmetry": "Response delay gap",
        "warm_cold_cycles": "Warm-cold flip",
        "boundary_setting_language": "Boundary-setting pattern",
        "unresolved_future_talk": "Plan suggested then dropped",
        "affection_distance_contradiction": "Affection-distance contradiction",
    }
    return labels.get(detector, detector)


def _summary_text(index: float, confidence: float, detector_results: list) -> str:
    top = sorted(detector_results, key=lambda d: d.score, reverse=True)[:2]
    top_names = ", ".join(d.detector for d in top if d.score > 0)
    if not top_names:
        top_names = "no strong mixed-signal detectors"
    return (
        f"Mixed Signal Index: {index}/100 with confidence {round(confidence * 100, 1)}%. "
        f"Primary contributors: {top_names}. "
        "This report describes communication patterns and does not diagnose people or predict outcomes."
    )
