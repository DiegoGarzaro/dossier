"""Async data access for document metadata."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


class DocumentRepository:
    """Repository for Document rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The request-scoped database session.
        """
        self._session = session

    async def get(self, document_id: int) -> Document | None:
        """Fetch a document by id.

        Args:
            document_id (int): The document id.

        Returns:
            Document | None: The document, or None if not found.
        """
        return await self._session.get(Document, document_id)

    async def add(self, document: Document) -> Document:
        """Persist new document metadata.

        Args:
            document (Document): The document to add.

        Returns:
            Document: The persisted document with its id populated.
        """
        self._session.add(document)
        await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        """Delete document metadata (FR-21).

        Args:
            document (Document): The document to delete.

        Returns:
            None
        """
        await self._session.delete(document)
        await self._session.flush()
