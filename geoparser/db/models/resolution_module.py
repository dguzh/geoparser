import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution import Resolution
    from geoparser.db.models.resolution_process import ResolutionProcess


class ResolutionModuleBase(SQLModel):
    """Base model for resolution module metadata."""

    name: str = Field(
        index=True
    )  # Name of the resolution module with index for faster lookups


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
    resolution_processes: list["ResolutionProcess"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ResolutionModuleCreate(ResolutionModuleBase):
    """Model for creating a new resolution module record."""


class ResolutionModuleUpdate(SQLModel):
    """Model for updating a resolution module record."""

    id: uuid.UUID
    name: t.Optional[str] = None
