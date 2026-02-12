import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.parsing.types import ParsedChat, ParsedMessage

WHATSAPP_LINE_RE = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),\s(\d{1,2}:\d{2})(?:\s?([APMapm]{2}))?\s-\s([^:]+):\s(.*)$")


def _parse_ts(date_part: str, time_part: str, ampm: str | None, timezone_name: str) -> datetime:
    tz = ZoneInfo(timezone_name)
    formats = ["%m/%d/%y %H:%M", "%d/%m/%y %H:%M", "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M"]
    if ampm:
        formats = ["%m/%d/%y %I:%M %p", "%d/%m/%y %I:%M %p", "%m/%d/%Y %I:%M %p", "%d/%m/%Y %I:%M %p"]
        raw = f"{date_part} {time_part} {ampm.upper()}"
    else:
        raw = f"{date_part} {time_part}"
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse WhatsApp timestamp: {raw}")


def parse_whatsapp_txt(path: str, timezone_name: str) -> ParsedChat:
    participants: set[str] = set()
    messages: list[ParsedMessage] = []
    current_index: int | None = None

    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            match = WHATSAPP_LINE_RE.match(line)
            if not match:
                if current_index is not None:
                    messages[current_index].text = f"{messages[current_index].text}\n{line}".strip()
                continue

            date_part, time_part, ampm, sender, text = match.groups()
            ts = _parse_ts(date_part, time_part, ampm, timezone_name)
            participants.add(sender.strip())
            messages.append(ParsedMessage(ts=ts, sender=sender.strip(), text=text.strip()))
            current_index = len(messages) - 1

    messages.sort(key=lambda m: m.ts)
    return ParsedChat(
        participants=sorted(participants),
        messages=messages,
        summary={"message_count": len(messages), "participant_count": len(participants), "parser": "whatsapp_txt"},
    )

