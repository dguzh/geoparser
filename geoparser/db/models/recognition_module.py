import typing as t
import uuid

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.recognition import RecognitionObject
    from geoparser.db.models.recognition_process import RecognitionSubject


class RecognitionModuleBase(SQLModel):
    """Base model for recognition module metadata."""

    config: t.Optional[dict] = Field(
        default=None, sa_type=JSON
    )  # Configuration as JSON which includes module_name


class RecognitionModule(RecognitionModuleBase, table=True):
    """
    Stores metadata about recognition modules.

    This includes configuration information and other details about specific
    recognition module instances. The module_name is stored in the config dictionary.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    recognition_objects: list["RecognitionObject"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    recognition_subjects: list["RecognitionSubject"] = Relationship(
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
    config: t.Optional[dict] = None
