import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.recognition import Recognition
    from geoparser.db.models.recognition_process import RecognitionProcess


class RecognitionModuleBase(SQLModel):
    """Base model for recognition module metadata."""

    name: str = Field(
        index=True
    )  # Name of the recognition module with index for faster lookups


class RecognitionModule(RecognitionModuleBase, table=True):
    """
    Stores metadata about recognition modules.

    This includes configuration information and other details about specific
    recognition module instances.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recognitions: list["Recognition"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    recognition_processes: list["RecognitionProcess"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class RecognitionModuleCreate(RecognitionModuleBase):
    """Model for creating a new recognition module record."""


class RecognitionModuleUpdate(SQLModel):
    """Model for updating a recognition module record."""

    id: uuid.UUID
    name: t.Optional[str] = None
