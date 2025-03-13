import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import (
    ResolutionModule,
    ResolutionModuleCreate,
    ResolutionModuleUpdate,
)


class ResolutionModuleRepository(BaseRepository[ResolutionModule]):
    """
    Repository for ResolutionModule model operations.
    """

    def __init__(self):
        super().__init__(ResolutionModule)

    def get_by_name(self, db: Session, name: str) -> t.Optional[ResolutionModule]:
        """
        Get a resolution module by name.

        Args:
            db: Database session
            name: Module name

        Returns:
            ResolutionModule if found, None otherwise
        """
        statement = select(ResolutionModule).where(ResolutionModule.name == name)
        return db.exec(statement).first()
