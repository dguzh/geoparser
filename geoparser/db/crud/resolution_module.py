import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import ResolutionModule


class ResolutionModuleRepository(BaseRepository[ResolutionModule]):
    """
    Repository for ResolutionModule model operations.
    """

    model = ResolutionModule

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> t.Optional[ResolutionModule]:
        """
        Get a resolution module by name.

        Note: This method returns the first module with the given name,
        regardless of configuration. Consider using get_by_name_and_config instead.

        Args:
            db: Database session
            name: Module name

        Returns:
            ResolutionModule if found, None otherwise
        """
        statement = select(ResolutionModule).where(ResolutionModule.name == name)
        return db.exec(statement).first()

    @classmethod
    def get_by_name_and_config(
        cls, db: Session, name: str, config: t.Optional[dict] = None
    ) -> t.Optional[ResolutionModule]:
        """
        Get a resolution module by name and configuration.

        This method allows finding a specific module instance by both its name and
        configuration, ensuring the exact module instance is retrieved.

        Args:
            db: Database session
            name: Module name
            config: Module configuration dict

        Returns:
            ResolutionModule if found, None otherwise
        """
        statement = select(ResolutionModule).where(
            ResolutionModule.name == name, ResolutionModule.config == config
        )
        return db.exec(statement).first()
