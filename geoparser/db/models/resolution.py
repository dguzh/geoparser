import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.location import Location
    from geoparser.db.models.resolution_module import ResolutionModule


class ResolutionBase(SQLModel):
    """Base model for the resolution process."""

    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolutionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class Resolution(ResolutionBase, table=True):
    """
    Records which resolution processes identified each location.

    This allows tracking of which module resolved a toponym to a specific location.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    location_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("location.id", ondelete="CASCADE"), nullable=False
        )
    )
    location: "Location" = Relationship(back_populates="resolutions")
    module: "ResolutionModule" = Relationship(back_populates="resolutions")


class ResolutionCreate(ResolutionBase):
    """Model for creating a new resolution record."""

    pass


class ResolutionUpdate(SQLModel):
    """Model for updating a resolution record."""

    id: uuid.UUID
    location_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
