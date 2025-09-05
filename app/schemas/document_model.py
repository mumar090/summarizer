from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class DocumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    URL: HttpUrl


class DocumentOut(BaseModel):
    document_uuid: str
    status: str
    name: str
    URL: str
    summary: Optional[str]
    data_progress: float
    error_message: Optional[str] = None


class Config:
    orm_mode = True