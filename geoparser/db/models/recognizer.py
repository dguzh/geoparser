import typing as t
import uuid

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.recognition import Recognition
    from geoparser.db.models.reference import Reference


class RecognizerBase(SQLModel):
    """Base model for recognizer metadata."""

    name: str = Field(index=True)
    config: t.Dict[str, t.Any] = Field(default_factory=dict, sa_type=JSON)


class Recognizer(RecognizerBase, table=True):
    """
    Stores metadata about recognizers.

    This includes configuration information and other details about specific
    recognizer instances.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    references: list["Reference"] = Relationship(
        back_populates="recognizer",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    recognitions: list["Recognition"] = Relationship(
        back_populates="recognizer",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        """
        Return a string representation of the recognizer.

        Returns:
            String with recognizer name and config parameters
        """
        config_str = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())
        return f"{self.name}({config_str})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the recognizer.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class RecognizerCreate(RecognizerBase):
    """Model for creating a new recognizer record."""


class RecognizerUpdate(SQLModel):
    """Model for updating a recognizer record."""

    id: uuid.UUID
    name: t.Optional[str] = None
    config: t.Optional[t.Dict[str, t.Any]] = None
