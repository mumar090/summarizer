from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, StatusEnum


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str, url: str) -> Document:
        doc = Document(name=name, URL=url, status=StatusEnum.PENDING, data_progress=0.0)
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get(self, document_uuid: str) -> Document | None:
        return await self.session.get(Document, document_uuid)

    async def mark_failed(self, doc: Document, message: str) -> Document:
        doc.status = StatusEnum.FAILED
        doc.error_message = message
        await self.session.flush()
        return doc
