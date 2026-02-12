from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import Job
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.job import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    upload = db.scalar(select(Upload).where(Upload.id == job.upload_id))
    if not upload or upload.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job

