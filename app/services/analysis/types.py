from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MessageView:
    id: str
    ts: datetime
    sender_id: str
    sender_name: str
    text: str


@dataclass(slots=True)
class DetectorResult:
    detector: str
    score: float
    explanation: str
    evidence_ids: list[str]

