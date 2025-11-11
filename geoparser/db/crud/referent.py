import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Referent


class ReferentRepository(BaseRepository[Referent]):
    """
    Repository for Referent model operations.
    """

    model = Referent

    @classmethod
    def get_by_reference(cls, db: Session, reference_id: uuid.UUID) -> t.List[Referent]:
        """
        Get all referents for a reference.

        Args:
            db: Database session
            reference_id: Reference ID

        Returns:
            List of referents
        """
        statement = select(Referent).where(Referent.reference_id == reference_id)
        return db.exec(statement).unique().all()
