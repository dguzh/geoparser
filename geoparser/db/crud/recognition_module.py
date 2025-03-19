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
    def get_by_config(cls, db: Session, config: dict) -> t.Optional[RecognitionModule]:
        """
        Get a recognition module by configuration.

        This method allows finding a specific module instance by its configuration,
        which must include the module_name to uniquely identify the module type.

        Args:
            db: Database session
            config: Module configuration dict (must include module_name)

        Returns:
            RecognitionModule if found, None otherwise
        """
        if "module_name" not in config:
            raise ValueError("Config must include module_name")

        statement = select(RecognitionModule).where(RecognitionModule.config == config)
        return db.exec(statement).first()
