from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Upload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "uploads"

    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    parsing_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    owner = relationship("User", back_populates="uploads")
    participants = relationship("Participant", back_populates="upload", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="upload", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="upload", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    excerpts = relationship("Excerpt", back_populates="upload", cascade="all, delete-orphan")

