import typing as t
import uuid

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution_object import ResolutionObject
    from geoparser.db.models.resolution_subject import ResolutionSubject


class ResolutionModuleBase(SQLModel):
    """Base model for resolution module metadata."""

    name: str = Field(index=True)
    config: t.Dict[str, t.Any] = Field(default_factory=dict, sa_type=JSON)


class ResolutionModule(ResolutionModuleBase, table=True):
    """
    Stores metadata about resolution modules.

    This includes configuration information and other details about specific
    resolution module instances.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resolution_objects: list["ResolutionObject"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    resolution_subjects: list["ResolutionSubject"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        """
        Return a string representation of the resolution module.

        Returns:
            String with module name and config parameters
        """
        config_str = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())
        return f"{self.name}({config_str})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the resolution module.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class ResolutionModuleCreate(ResolutionModuleBase):
    """Model for creating a new resolution module record."""


class ResolutionModuleUpdate(SQLModel):
    """Model for updating a resolution module record."""

    id: uuid.UUID
    name: t.Optional[str] = None
    config: t.Optional[t.Dict[str, t.Any]] = None
