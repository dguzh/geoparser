import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.location import Location
    from geoparser.db.models.resolution_module import ResolutionModule


class ResolutionObjectBase(SQLModel):
    """Base model for resolution object data."""

    location_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("location.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolutionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class ResolutionObject(ResolutionObjectBase, table=True):
    """
    Represents a resolution object.

    Tracks which resolution module identified a specific location for a toponym.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    location: "Location" = Relationship(back_populates="resolution_objects")
    module: "ResolutionModule" = Relationship(back_populates="resolution_objects")


class ResolutionObjectCreate(ResolutionObjectBase):
    """Model for creating a new resolution object."""


class ResolutionObjectUpdate(SQLModel):
    """Model for updating an existing resolution object."""

    id: uuid.UUID
    location_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
