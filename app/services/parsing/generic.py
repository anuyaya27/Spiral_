import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.parsing.types import ParsedChat, ParsedMessage


def parse_generic_json(path: str, timezone_name: str) -> ParsedChat:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    participants = [str(p) for p in payload.get("participants", [])]
    messages_payload = payload.get("messages", [])
    parsed_messages: list[ParsedMessage] = []
    seen_participants = set(participants)
    tz = ZoneInfo(timezone_name)

    for row in messages_payload:
        ts_raw = row.get("ts")
        sender = str(row.get("sender", "unknown"))
        text = str(row.get("text", ""))
        if not ts_raw:
            continue
        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=tz)
        seen_participants.add(sender)
        parsed_messages.append(ParsedMessage(ts=ts, sender=sender, text=text))

    parsed_messages.sort(key=lambda m: m.ts)
    return ParsedChat(
        participants=sorted(seen_participants),
        messages=parsed_messages,
        summary={"message_count": len(parsed_messages), "participant_count": len(seen_participants), "parser": "generic_json"},
    )

