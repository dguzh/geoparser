import typing as t

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Project


class ProjectRepository(BaseRepository[Project]):
    """
    Repository for Project model operations.
    """

    model = Project

    @classmethod
    def get_by_name(cls, db: Session, name: str) -> t.Optional[Project]:
        """
        Get a project by name.

        Args:
            db: Database session
            name: Project name

        Returns:
            Project if found, None otherwise
        """
        statement = select(Project).where(Project.name == name)
        return db.exec(statement).first()
