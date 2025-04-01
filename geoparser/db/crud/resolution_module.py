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
    def get_by_name_and_config(
        cls, db: Session, name: str, config: dict
    ) -> t.Optional[ResolutionModule]:
        """
        Get a resolution module by name and configuration.

        This method allows finding a specific module instance by its name and configuration.

        Args:
            db: Database session
            name: Name of the module
            config: Module configuration dict

        Returns:
            ResolutionModule if found, None otherwise
        """
        statement = select(ResolutionModule).where(
            (ResolutionModule.name == name) & (ResolutionModule.config == config)
        )
        return db.exec(statement).first()
