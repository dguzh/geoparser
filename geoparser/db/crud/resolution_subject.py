import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, ResolutionSubject, Toponym


class ResolutionSubjectRepository(BaseRepository[ResolutionSubject]):
    """
    Repository for ResolutionSubject model operations.
    """

    model = ResolutionSubject

    @classmethod
    def get_by_toponym(
        cls, db: DBSession, toponym_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Get all resolution subjects for a toponym.

        Args:
            db: Database session
            toponym_id: ID of the toponym

        Returns:
            List of resolution subjects
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.toponym_id == toponym_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_module(
        cls, db: DBSession, module_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Get all resolution subjects for a module.

        Args:
            db: Database session
            module_id: ID of the resolution module

        Returns:
            List of resolution subjects
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.module_id == module_id
        )
        return db.exec(statement).all()

    @classmethod
    def get_by_toponym_and_module(
        cls, db: DBSession, toponym_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[ResolutionSubject]:
        """
        Get a resolution subject for a specific toponym and module.

        Args:
            db: Database session
            toponym_id: ID of the toponym
            module_id: ID of the resolution module

        Returns:
            ResolutionSubject if found, None otherwise
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.toponym_id == toponym_id,
            ResolutionSubject.module_id == module_id,
        )
        return db.exec(statement).first()

    @classmethod
    def get_unprocessed_toponyms(
        cls, db: DBSession, session_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.List[Toponym]:
        """
        Get all toponyms from a session that have not been processed by a specific module.

        This is done by retrieving all toponyms for the session and excluding those
        that have a corresponding resolution subject record for the given module.

        Args:
            db: Database session
            session_id: ID of the session containing the documents with toponyms
            module_id: ID of the resolution module

        Returns:
            List of unprocessed Toponym objects
        """
        # Get all toponyms for documents in the session that haven't been processed
        statement = (
            select(Toponym)
            .join(Document, Toponym.document_id == Document.id)
            .where(
                Document.session_id == session_id,
                not_(
                    Toponym.id.in_(
                        select(ResolutionSubject.toponym_id).where(
                            ResolutionSubject.module_id == module_id
                        )
                    )
                ),
            )
        )
        return db.exec(statement).all()

    @classmethod
    def create_many(
        cls, db: DBSession, toponym_ids: t.List[uuid.UUID], module_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Create multiple resolution subject records at once.

        Args:
            db: Database session
            toponym_ids: List of toponym IDs
            module_id: ID of the resolution module

        Returns:
            List of created ResolutionSubject objects
        """
        subjects = []
        for toponym_id in toponym_ids:
            subject = ResolutionSubject(toponym_id=toponym_id, module_id=module_id)
            db.add(subject)
            subjects.append(subject)

        db.flush()  # Flush to assign IDs but don't commit yet
        return subjects
