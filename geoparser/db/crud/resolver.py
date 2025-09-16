import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Resolver


class ResolverRepository(BaseRepository[Resolver]):
    """
    Repository for Resolver model operations.
    """

    model = Resolver

    @classmethod
    def get_by_name_and_config(
        cls, db: Session, name: str, config: dict
    ) -> t.Optional[Resolver]:
        """
        Get a resolver by name and configuration.

        This method allows finding a specific resolver instance by its name and configuration.

        Args:
            db: Database session
            name: Name of the resolver
            config: Resolver configuration dict

        Returns:
            Resolver if found, None otherwise
        """
        statement = select(Resolver).where(
            (Resolver.name == name) & (Resolver.config == config)
        )
        return db.exec(statement).unique().first()
