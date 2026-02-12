from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    upload = relationship("Upload", back_populates="messages")
    sender = relationship("Participant", back_populates="messages")

