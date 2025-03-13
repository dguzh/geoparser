import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution import Resolution


class ResolutionModuleBase(SQLModel):
    """Base model for resolution module metadata."""

    name: str  # Name of the resolution module


class ResolutionModule(ResolutionModuleBase, table=True):
    """
    Stores metadata about resolution modules.

    This includes configuration information and other details about specific
    resolution module instances.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resolutions: list["Resolution"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ResolutionModuleCreate(ResolutionModuleBase):
    """Model for creating a new resolution module record."""

    pass


class ResolutionModuleUpdate(SQLModel):
    """Model for updating a resolution module record."""

    id: uuid.UUID
    name: t.Optional[str] = None
