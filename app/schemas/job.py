from datetime import datetime

from pydantic import BaseModel


class JobRead(BaseModel):
    id: str
    upload_id: str
    status: str
    progress: int
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

