from sqlalchemy import JSON, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    mixed_signal_index: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    upload = relationship("Upload", back_populates="report")

