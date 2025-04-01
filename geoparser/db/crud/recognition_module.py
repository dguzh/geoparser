import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import RecognitionModule


class RecognitionModuleRepository(BaseRepository[RecognitionModule]):
    """
    Repository for RecognitionModule model operations.
    """

    model = RecognitionModule

    @classmethod
    def get_by_name_and_config(
        cls, db: Session, name: str, config: dict
    ) -> t.Optional[RecognitionModule]:
        """
        Get a recognition module by name and configuration.

        This method allows finding a specific module instance by its name and configuration.

        Args:
            db: Database session
            name: Name of the module
            config: Module configuration dict

        Returns:
            RecognitionModule if found, None otherwise
        """
        statement = select(RecognitionModule).where(
            (RecognitionModule.name == name) & (RecognitionModule.config == config)
        )
        return db.exec(statement).first()
