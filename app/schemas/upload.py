from datetime import datetime

from pydantic import BaseModel


class UploadCreateResponse(BaseModel):
    upload_id: str
    message_count: int


class UploadRead(BaseModel):
    id: str
    status: str
    created_at: datetime
    platform: str
    timezone: str
    parsing_summary: dict

    model_config = {"from_attributes": True}
