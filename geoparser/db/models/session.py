import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document, DocumentCreate


class SessionBase(SQLModel):
    """Base model for session data."""

    name: str = Field(index=True)


class Session(SessionBase, table=True):
    """
    Represents a processing session.

    A session groups together related documents for processing.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    documents: list["Document"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class SessionCreate(SessionBase):
    """Model for creating a new session."""

    pass


class SessionUpdate(SQLModel):
    """Model for updating an existing session."""

    id: uuid.UUID
    name: t.Optional[str] = None
