from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.upload import Upload
from app.services.storage import delete_file_if_exists


def run_retention_cleanup(db: Session) -> int:
    now = datetime.now(timezone.utc)
    stale = db.scalars(select(Upload).where(Upload.retention_until < now)).all()
    deleted = 0
    for upload in stale:
        delete_file_if_exists(upload.file_path)
        db.delete(upload)
        deleted += 1
    db.commit()
    return deleted

