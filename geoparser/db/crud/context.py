import typing as t
import uuid

from sqlmodel import Session, select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models.context import Context


class ContextRepository(BaseRepository[Context]):
    """
    Repository for Context model operations.
    """

    model = Context

    @classmethod
    def get_by_project(cls, db: Session, project_id: uuid.UUID) -> t.List[Context]:
        """
        Get all context records for a project.

        Args:
            db: Database session
            project_id: ID of the project

        Returns:
            List of context records
        """
        statement = select(Context).where(Context.project_id == project_id)
        return db.exec(statement).unique().all()

    @classmethod
    def get_by_project_and_tag(
        cls, db: Session, project_id: uuid.UUID, tag: str
    ) -> t.Optional[Context]:
        """
        Get a specific context record by project and tag.

        Args:
            db: Database session
            project_id: ID of the project
            tag: Tag identifier

        Returns:
            Context record if found, None otherwise
        """
        statement = select(Context).where(
            Context.project_id == project_id,
            Context.tag == tag,
        )
        return db.exec(statement).unique().first()
