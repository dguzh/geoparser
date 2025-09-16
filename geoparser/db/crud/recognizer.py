import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Recognizer


class RecognizerRepository(BaseRepository[Recognizer]):
    """
    Repository for Recognizer model operations.
    """

    model = Recognizer

    @classmethod
    def get_by_name_and_config(
        cls, db: Session, name: str, config: dict
    ) -> t.Optional[Recognizer]:
        """
        Get a recognizer by name and configuration.

        This method allows finding a specific recognizer instance by its name and configuration.

        Args:
            db: Database session
            name: Name of the recognizer
            config: Recognizer configuration dict

        Returns:
            Recognizer if found, None otherwise
        """
        statement = select(Recognizer).where(
            (Recognizer.name == name) & (Recognizer.config == config)
        )
        return db.exec(statement).unique().first()
