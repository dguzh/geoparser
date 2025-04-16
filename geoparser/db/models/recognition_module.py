import typing as t
import uuid

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.recognition_object import RecognitionObject
    from geoparser.db.models.recognition_subject import RecognitionSubject


class RecognitionModuleBase(SQLModel):
    """Base model for recognition module metadata."""

    name: str = Field(index=True)
    config: t.Dict[str, t.Any] = Field(default_factory=dict, sa_type=JSON)


class RecognitionModule(RecognitionModuleBase, table=True):
    """
    Stores metadata about recognition modules.

    This includes configuration information and other details about specific
    recognition module instances.
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
    name: t.Optional[str] = None
    config: t.Optional[t.Dict[str, t.Any]] = None


class RecognitionModuleRead(SQLModel):
    """
    Model for reading recognition module data.

    Only exposes the id, name and config of a recognition module.
    """

    id: uuid.UUID
    name: str
    config: t.Dict[str, t.Any]

    model_config = {"from_attributes": True}

    def __str__(self) -> str:
        """
        Return a string representation of the recognition module.

        Returns:
            String with module name and config parameters
        """
        config_str = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())
        return f"{self.name}({config_str})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the recognition module.

        Returns:
            Same as __str__ method
        """
        return self.__str__()
