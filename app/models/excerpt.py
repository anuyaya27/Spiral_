from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Excerpt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "excerpts"

    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    upload = relationship("Upload", back_populates="excerpts")

