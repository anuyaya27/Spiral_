from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    upload = relationship("Upload", back_populates="jobs")

