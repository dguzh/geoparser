import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, Reference, ResolutionSubject


class ResolutionSubjectRepository(BaseRepository[ResolutionSubject]):
    """
    Repository for ResolutionSubject model operations.
    """

    model = ResolutionSubject

    @classmethod
    def get_by_reference(
        cls, db: Session, reference_id: uuid.UUID
    ) -> t.List[ResolutionSubject]:
        """
        Get all resolution subjects for a reference.

        Args:
            db: Database session
            reference_id: ID of the reference

        Returns:
            List of resolution subjects
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.reference_id == reference_id
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
    def get_by_reference_and_module(
        cls, db: Session, reference_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[ResolutionSubject]:
        """
        Get a resolution subject for a specific reference and module.

        Args:
            db: Database session
            reference_id: ID of the reference
            module_id: ID of the resolution module

        Returns:
            ResolutionSubject if found, None otherwise
        """
        statement = select(ResolutionSubject).where(
            ResolutionSubject.reference_id == reference_id,
            ResolutionSubject.module_id == module_id,
        )
        return db.exec(statement).unique().first()

    @classmethod
    def get_unprocessed_references(
        cls, db: Session, project_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.List[Reference]:
        """
        Get all references from a project that have not been processed by a specific module.

        This is done by retrieving all references for the project and excluding those
        that have a corresponding resolution subject record for the given module.

        Args:
            db: Database session
            project_id: ID of the project containing the documents with references
            module_id: ID of the resolution module

        Returns:
            List of unprocessed Reference objects
        """
        # Get all references for documents in the project that haven't been processed
        statement = (
            select(Reference)
            .join(Document, Reference.document_id == Document.id)
            .where(
                Document.project_id == project_id,
                not_(
                    Reference.id.in_(
                        select(ResolutionSubject.reference_id).where(
                            ResolutionSubject.module_id == module_id
                        )
                    )
                ),
            )
        )
        return db.exec(statement).unique().all()
