from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ParsedMessage:
    ts: datetime
    sender: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ParsedChat:
    participants: list[str]
    messages: list[ParsedMessage]
    summary: dict

