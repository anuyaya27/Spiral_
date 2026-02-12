from datetime import datetime

from pydantic import BaseModel


class ReportRead(BaseModel):
    upload_id: str
    created_at: datetime
    mixed_signal_index: float
    confidence: float
    summary_text: str
    report_json: dict


class HighlightRead(BaseModel):
    window_start: datetime
    window_end: datetime
    label: str
    detectors_triggered: list[str]
    excerpts: list[dict]

