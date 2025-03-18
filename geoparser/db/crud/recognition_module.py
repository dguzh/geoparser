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
    def get_by_name(cls, db: Session, name: str) -> t.Optional[RecognitionModule]:
        """
        Get a recognition module by name.

        Note: This method returns the first module with the given name,
        regardless of configuration. Consider using get_by_name_and_config instead.

        Args:
            db: Database session
            name: Module name

        Returns:
            RecognitionModule if found, None otherwise
        """
        statement = select(RecognitionModule).where(RecognitionModule.name == name)
        return db.exec(statement).first()

    @classmethod
    def get_by_name_and_config(
        cls, db: Session, name: str, config: t.Optional[dict] = None
    ) -> t.Optional[RecognitionModule]:
        """
        Get a recognition module by name and configuration.

        This method allows finding a specific module instance by both its name and
        configuration, ensuring the exact module instance is retrieved.

        Args:
            db: Database session
            name: Module name
            config: Module configuration dict

        Returns:
            RecognitionModule if found, None otherwise
        """
        statement = select(RecognitionModule).where(
            RecognitionModule.name == name, RecognitionModule.config == config
        )
        return db.exec(statement).first()
