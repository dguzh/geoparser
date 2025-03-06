import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.location import Location


class ResolutionModuleBase(SQLModel):
    """Base model for the resolution module bridging table."""

    resolution_module: (
        str  # Name of the resolution module that identified this location
    )


class ResolutionModule(ResolutionModuleBase, table=True):
    """
    Bridging table that tracks which resolution modules identified each location.

    This allows tracking of which module resolved a toponym to a specific location.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    location_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("location.id", ondelete="CASCADE"), nullable=False
        )
    )
    location: "Location" = Relationship(back_populates="resolutions")


class ResolutionModuleCreate(ResolutionModuleBase):
    """Model for creating a new resolution module record."""

    pass


class ResolutionModuleUpdate(SQLModel):
    """Model for updating a resolution module record."""

    id: uuid.UUID
    location_id: t.Optional[uuid.UUID] = None
    resolution_module: t.Optional[str] = None
