import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    FETCHING = "FETCHING"
    EXTRACTING = "EXTRACTING"
    SUMMARIZING = "SUMMARIZING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


TERMINAL_STATUSES = frozenset({StatusEnum.SUCCESS, StatusEnum.FAILED})


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    document_uuid: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    URL: Mapped[str] = mapped_column("url", Text)
    # native_enum=False stores a VARCHAR, so adding a status never needs a DB enum migration.
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum, native_enum=False, length=20), default=StatusEnum.PENDING, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    data_progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
