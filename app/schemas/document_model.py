from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.db.models import StatusEnum


class DocumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    URL: HttpUrl


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_uuid: str
    status: StatusEnum
    name: str
    URL: str
    summary: str | None
    data_progress: float = Field(..., ge=0.0, le=1.0)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
