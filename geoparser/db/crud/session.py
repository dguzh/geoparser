import typing as t
import uuid

from sqlmodel import Session as DBSession
from sqlmodel import select

from geoparser.db.crud.base import BaseRepository
from geoparser.db.models import Session, SessionCreate, SessionUpdate


class SessionRepository(BaseRepository[Session]):
    """
    Repository for Session model operations.
    """

    model = Session

    @classmethod
    def get_by_name(cls, db: DBSession, name: str) -> t.Optional[Session]:
        """
        Get a session by name.

        Args:
            db: Database session
            name: Session name

        Returns:
            Session if found, None otherwise
        """
        statement = select(Session).where(Session.name == name)
        return db.exec(statement).first()
