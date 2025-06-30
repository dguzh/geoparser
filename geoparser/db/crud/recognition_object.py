import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import RecognitionObject


class RecognitionObjectRepository(BaseRepository[RecognitionObject]):
    """
    Repository for RecognitionObject model operations.
    """

    model = RecognitionObject

    @classmethod
    def get_by_reference(
        cls, db: Session, reference_id: uuid.UUID
    ) -> t.List[RecognitionObject]:
        """
        Get all recognition objects for a reference.

        Args:
            db: Database session
            reference_id: ID of the reference

        Returns:
            List of recognition objects
        """
        statement = select(RecognitionObject).where(
            RecognitionObject.reference_id == reference_id
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_module(
        cls, db: Session, module_id: uuid.UUID
    ) -> t.List[RecognitionObject]:
        """
        Get all recognition objects for a module.

        Args:
            db: Database session
            module_id: ID of the recognition module

        Returns:
            List of recognition objects
        """
        statement = select(RecognitionObject).where(
            RecognitionObject.module_id == module_id
        )
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_reference_and_module(
        cls, db: Session, reference_id: uuid.UUID, module_id: uuid.UUID
    ) -> t.Optional[RecognitionObject]:
        """
        Get a recognition object for a specific reference and module.

        Args:
            db: Database session
            reference_id: ID of the reference
            module_id: ID of the recognition module

        Returns:
            Recognition object if found, None otherwise
        """
        statement = select(RecognitionObject).where(
            RecognitionObject.reference_id == reference_id,
            RecognitionObject.module_id == module_id,
        )
        return db.exec(statement).unique().first()
