import enum
import uuid
from sqlalchemy import Column, String, Text, Float, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    FETCHING = "FETCHING"
    EXTRACTING = "EXTRACTING"
    SUMMARIZING = "SUMMARIZING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"


    document_uuid = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    URL = Column(Text, nullable=False, index=True)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING)
    summary = Column(Text, nullable=True)
    data_progress = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)