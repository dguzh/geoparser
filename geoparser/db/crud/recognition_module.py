import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import (
    RecognitionModule,
    RecognitionModuleCreate,
    RecognitionModuleUpdate,
)


class RecognitionModuleRepository(BaseRepository[RecognitionModule]):
    """
    Repository for RecognitionModule model operations.
    """

    def __init__(self):
        super().__init__(RecognitionModule)

    def get_by_name(self, db: Session, name: str) -> t.Optional[RecognitionModule]:
        """
        Get a recognition module by name.

        Args:
            db: Database session
            name: Module name

        Returns:
            RecognitionModule if found, None otherwise
        """
        statement = select(RecognitionModule).where(RecognitionModule.name == name)
        return db.exec(statement).first()


recognition_module_repository = RecognitionModuleRepository()
