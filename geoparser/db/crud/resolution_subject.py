import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, ResolutionSubject, Toponym


class ResolutionSubjectRepository(BaseRepository[ResolutionSubject]):
    """
    Repository for ResolutionSubject model operations.
    """

    model = ResolutionSubject

    @classmethod
    def get_by_toponym(
        cls, db: Session, toponym_id: uuid.UUID
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
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
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
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_toponym_and_module(
        cls, db: Session, toponym_id: uuid.UUID, module_id: uuid.UUID
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
        return db.exec(statement).unique().first()

    @classmethod
    def get_unprocessed_toponyms(
        cls, db: Session, project_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.List[Toponym]:
        """
        Get all toponyms from a project that have not been processed by a specific module.

        This is done by retrieving all toponyms for the project and excluding those
        that have a corresponding resolution subject record for the given module.

        Args:
            db: Database session
            project_id: ID of the project containing the documents with toponyms
            module_id: ID of the resolution module

        Returns:
            List of unprocessed Toponym objects
        """
        # Get all toponyms for documents in the project that haven't been processed
        statement = (
            select(Toponym)
            .join(Document, Toponym.document_id == Document.id)
            .where(
                Document.project_id == project_id,
                not_(
                    Toponym.id.in_(
                        select(ResolutionSubject.toponym_id).where(
                            ResolutionSubject.module_id == module_id
                        )
                    )
                ),
            )
        )
        return db.exec(statement).unique().all()
