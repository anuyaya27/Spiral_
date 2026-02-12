from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participants"

    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    upload = relationship("Upload", back_populates="participants")
    messages = relationship("Message", back_populates="sender")

