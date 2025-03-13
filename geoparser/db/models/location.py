import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution import Resolution
    from geoparser.db.models.toponym import Toponym


class LocationBase(SQLModel):
    """
    Base model for location data.

    Contains the core fields that identify a location in a gazetteer.
    """

    location_id: str  # ID of the location in the gazetteer
    confidence: t.Optional[float] = None  # Optional confidence score


class Location(LocationBase, table=True):
    """
    Represents a resolved location for a toponym.

    A location is a specific place that a toponym might refer to.
    Each toponym can have multiple potential locations with different confidence scores.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    toponym: "Toponym" = Relationship(back_populates="locations")
    resolutions: list["Resolution"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class LocationCreate(LocationBase):
    """
    Model for creating a new location.

    Includes the toponym_id to associate the location with a toponym.
    """

    toponym_id: uuid.UUID


class LocationUpdate(SQLModel):
    """Model for updating an existing location."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    location_id: t.Optional[str] = None
    confidence: t.Optional[float] = None
