import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.parsing.types import ParsedChat, ParsedMessage


def _parse_imessage_ts(value: str | int | float, timezone_name: str) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z"):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(timezone_name))
    return dt


def parse_imessage_json(path: str, timezone_name: str) -> ParsedChat:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    participants = [str(p) for p in payload.get("participants", [])]
    rows = payload.get("messages", [])
    parsed: list[ParsedMessage] = []
    discovered: set[str] = set(participants)
    for row in rows:
        sender = str(row.get("sender") or row.get("from") or "unknown")
        text = str(row.get("text") or "")
        ts_value = row.get("ts") or row.get("timestamp") or row.get("date")
        if ts_value is None:
            continue
        ts = _parse_imessage_ts(ts_value, timezone_name)
        discovered.add(sender)
        parsed.append(ParsedMessage(ts=ts, sender=sender, text=text, metadata={"source": "imessage"}))
    parsed.sort(key=lambda m: m.ts)
    return ParsedChat(
        participants=sorted(discovered),
        messages=parsed,
        summary={"message_count": len(parsed), "participant_count": len(discovered), "parser": "imessage_json"},
    )

