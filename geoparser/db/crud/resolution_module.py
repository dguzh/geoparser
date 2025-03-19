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
    def get_by_config(cls, db: Session, config: dict) -> t.Optional[ResolutionModule]:
        """
        Get a resolution module by configuration.

        This method allows finding a specific module instance by its configuration,
        which must include the module_name to uniquely identify the module type.

        Args:
            db: Database session
            config: Module configuration dict (must include module_name)

        Returns:
            ResolutionModule if found, None otherwise
        """
        if "module_name" not in config:
            raise ValueError("Config must include module_name")

        statement = select(ResolutionModule).where(ResolutionModule.config == config)
        return db.exec(statement).first()
