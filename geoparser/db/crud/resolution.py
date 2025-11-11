import typing as t
import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, Reference, Resolution


class ResolutionRepository(BaseRepository[Resolution]):
    """
    Repository for Resolution model operations.
    """

    model = Resolution

    @classmethod
    def get_by_reference(
        cls, db: Session, reference_id: uuid.UUID
    ) -> t.List[Resolution]:
        """
        Get all resolutions for a reference.

        Args:
            db: Database session
            reference_id: ID of the reference

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.reference_id == reference_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_resolver(cls, db: Session, resolver_id: str) -> t.List[Resolution]:
        """
        Get all resolutions for a resolver.

        Args:
            db: Database session
            resolver_id: ID of the resolver

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.resolver_id == resolver_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_reference_and_resolver(
        cls, db: Session, reference_id: uuid.UUID, resolver_id: str
    ) -> t.Optional[Resolution]:
        """
        Get a resolution for a specific reference and resolver.

        Args:
            db: Database session
            reference_id: ID of the reference
            resolver_id: ID of the resolver

        Returns:
            Resolution if found, None otherwise
        """
        statement = select(Resolution).where(
            Resolution.reference_id == reference_id,
            Resolution.resolver_id == resolver_id,
        )
        return db.exec(statement).unique().first()

    @classmethod
    def get_unprocessed_references(
        cls, db: Session, project_id: uuid.UUID, resolver_id: str
    ) -> t.List[Reference]:
        """
        Get all references from a project that have not been processed by a specific resolver.

        This is done by retrieving all references for the project and excluding those
        that have a corresponding resolution record for the given resolver.

        Args:
            db: Database session
            project_id: ID of the project containing the documents with references
            resolver_id: ID of the resolver

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
                        select(Resolution.reference_id).where(
                            Resolution.resolver_id == resolver_id
                        )
                    )
                ),
            )
        )
        return db.exec(statement).unique().all()
