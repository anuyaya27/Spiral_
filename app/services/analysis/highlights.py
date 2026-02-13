from datetime import datetime


def build_highlights(report_payload: dict, top_n: int = 10) -> list[dict]:
    highlights: list[dict] = []
    signals = report_payload.get("signals", []) if isinstance(report_payload, dict) else []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        signal_name = str(signal.get("name", "")).strip()
        signal_type = _signal_type(signal_name)
        tags = [signal_name] if signal_name else []
        evidence_rows = signal.get("evidence", [])
        for row in evidence_rows:
            if not isinstance(row, dict):
                continue
            excerpt = str(row.get("excerpt", "")).strip()
            if not excerpt:
                continue
            ts = row.get("timestamp")
            sender = str(row.get("sender", "Unknown")).strip() or "Unknown"
            highlights.append(
                {
                    "type": signal_type,
                    "label": signal_name or "Signal evidence",
                    "timestamp": _safe_iso(ts),
                    "sender": sender,
                    "excerpt": excerpt,
                    "tags": tags,
                }
            )

    # Fallback to timeline when signal evidence is missing.
    if not highlights:
        timeline = report_payload.get("timeline", []) if isinstance(report_payload, dict) else []
        for row in timeline[:top_n]:
            if not isinstance(row, dict):
                continue
            row_type = str(row.get("type", "mixed")).strip() or "mixed"
            normalized_type = "mixed_signal" if row_type == "mixed" else ("slow_reply" if row_type == "cool" else "mixed_signal")
            highlights.append(
                {
                    "type": normalized_type,
                    "label": "Timeline evidence",
                    "timestamp": _safe_iso(row.get("timestamp")),
                    "sender": str(row.get("sender", "Unknown")).strip() or "Unknown",
                    "excerpt": str(row.get("message", "")).strip(),
                    "tags": [str(tag) for tag in row.get("tags", []) if str(tag).strip()],
                }
            )

    # Keep top N red flags first, then fill with others.
    red_flags = [item for item in highlights if item.get("type") == "red_flag"][:top_n]
    others = [item for item in highlights if item.get("type") != "red_flag"][: max(0, top_n - len(red_flags))]
    merged = red_flags + others
    return merged[:top_n]


def enrich_report_for_ui(report_payload: dict, top_n: int = 10) -> dict:
    payload = dict(report_payload or {})
    stats = dict(payload.get("stats") or {})
    highlights = build_highlights(payload, top_n=top_n)

    # If reply-delay metric suggests asymmetry, try to expose at least one slow-reply highlight.
    reply_delay_ratio = _as_float(stats.get("reply_delay_ratio", 1.0), default=1.0)
    slow_count = sum(1 for item in highlights if item.get("type") == "slow_reply")
    if reply_delay_ratio >= 1.0 and slow_count == 0:
        synthetic = _slow_reply_from_timeline(payload)
        if synthetic:
            highlights.insert(0, synthetic)
            slow_count = 1
    if slow_count == 0:
        stats["reply_delay_ratio"] = 1.0

    # Keep stats.red_flags consistent with evidence list.
    red_count = sum(1 for item in highlights if item.get("type") == "red_flag")
    stats["red_flags"] = int(red_count)

    payload["highlights"] = highlights[:top_n]
    payload["stats"] = stats
    return payload


def _signal_type(name: str) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ("reply", "latency", "delay", "response")):
        return "slow_reply"
    if any(token in lowered for token in ("boundary", "contradiction", "unresolved", "red flag", "distance", "warm-cold", "warm cold")):
        return "red_flag"
    return "mixed_signal"


def _safe_iso(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raw = str(value or "").strip()
    return raw or ""


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _slow_reply_from_timeline(payload: dict) -> dict | None:
    timeline = payload.get("timeline", []) if isinstance(payload, dict) else []
    for row in timeline:
        if not isinstance(row, dict):
            continue
        row_type = str(row.get("type", "")).strip().lower()
        tags = [str(tag) for tag in row.get("tags", [])]
        tag_text = " ".join(tags).lower()
        if row_type == "cool" or "slow" in tag_text or "delay" in tag_text or "latency" in tag_text:
            excerpt = str(row.get("message", "")).strip()
            if not excerpt:
                continue
            return {
                "type": "slow_reply",
                "label": "Reply delay asymmetry",
                "timestamp": _safe_iso(row.get("timestamp")),
                "sender": str(row.get("sender", "Unknown")).strip() or "Unknown",
                "excerpt": excerpt,
                "tags": tags[:3],
            }
    return None
