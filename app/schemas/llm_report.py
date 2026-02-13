from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    timestamp: datetime
    excerpt: str
    sender: str


class SignalItem(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    explanation: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class TimelineItem(BaseModel):
    timestamp: datetime
    message: str
    tags: list[str] = Field(default_factory=list)
    type: Literal["warm", "cool", "mixed"]


class StatsPayload(BaseModel):
    initiation_percent: float
    reply_delay_ratio: float
    red_flags: int


class HighlightItem(BaseModel):
    type: Literal["red_flag", "slow_reply", "mixed_signal"]
    label: str
    timestamp: str
    sender: str
    excerpt: str
    tags: list[str] = Field(default_factory=list)


class LLMReport(BaseModel):
    mixed_signal_index: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    summary: str
    timeline: list[TimelineItem] = Field(default_factory=list, max_length=10)
    stats: StatsPayload
    signals: list[SignalItem] = Field(default_factory=list)
    highlights: list[HighlightItem] = Field(default_factory=list)
