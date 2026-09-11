import uuid

from sqlalchemy import not_
from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Document, Reference, Resolution

# Spelled out rather than left to SQLAlchemy so the join reads plainly at the
# call site. document_id is the only foreign key from Reference to Document,
# so a mutant that drops or blanks this expression produces the same ON
# clause -- which is why it is exempt while the query around it is not.
_REFERENCE_TO_DOCUMENT = Reference.document_id == Document.id  # pragma: no mutate  # fmt: skip


class ResolutionRepository(BaseRepository[Resolution]):
    """
    Repository for Resolution model operations.
    """

    model = Resolution

    @classmethod
    def get_by_reference(cls, db: Session, reference_id: uuid.UUID) -> list[Resolution]:
        """
        Get all resolutions for a reference.

        Args:
            db: Database session
            reference_id: ID of the reference

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.reference_id == reference_id)
        return list(db.exec(statement).unique().all())

    @classmethod
    def get_by_resolver(cls, db: Session, resolver_id: str) -> list[Resolution]:
        """
        Get all resolutions for a resolver.

        Args:
            db: Database session
            resolver_id: ID of the resolver

        Returns:
            List of resolutions
        """
        statement = select(Resolution).where(Resolution.resolver_id == resolver_id)
        return list(db.exec(statement).unique().all())

    @classmethod
    def get_by_reference_and_resolver(
        cls, db: Session, reference_id: uuid.UUID, resolver_id: str
    ) -> Resolution | None:
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
    ) -> list[Reference]:
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
        # Get all references for documents in the project that haven't been
        # processed. The join is its own statement so its pragma has somewhere
        # to sit: mutmut only reads a trailing pragma on a statement line, not
        # on a link in a chained expression.
        # SQLModel fields are annotated with their instance type, but at class
        # level they are SQLAlchemy column expressions. No checker models that
        # duality without a SQLAlchemy plugin.
        joined = select(Reference).join(Document, _REFERENCE_TO_DOCUMENT)  # ty: ignore[invalid-argument-type]  # pragma: no mutate  # fmt: skip
        statement = joined.where(
            Document.project_id == project_id,
            not_(
                Reference.id.in_(  # ty: ignore[unresolved-attribute]
                    select(Resolution.reference_id).where(
                        Resolution.resolver_id == resolver_id
                    )
                )
            ),
        )
        return list(db.exec(statement).unique().all())
