import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution_module import ResolutionModuleRead
    from geoparser.db.models.resolution_object import ResolutionObject
    from geoparser.db.models.toponym import Toponym


class LocationBase(SQLModel):
    """
    Base model for location data.

    Contains the location_id which references a gazetteer entry,
    as well as an optional confidence score.
    """

    location_id: str
    confidence: t.Optional[float] = None


class Location(LocationBase, table=True):
    """
    Represents a resolved location for a toponym.

    A location is a specific place in a gazetteer that a toponym refers to.
    Each toponym can have multiple potential locations, reflecting ambiguity in the text.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    toponym: "Toponym" = Relationship(back_populates="locations")
    resolution_objects: list["ResolutionObject"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",
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
    location_id: t.Optional[str] = None
    confidence: t.Optional[float] = None


class LocationRead(SQLModel):
    """
    Model for reading location data.

    Only exposes the id, toponym_id, location_id and confidence of a location.
    """

    id: uuid.UUID
    toponym_id: uuid.UUID
    location_id: str
    confidence: t.Optional[float] = None
    modules: list["ResolutionModuleRead"] = []

    model_config = {"from_attributes": True}

    def __str__(self) -> str:
        """
        Return a string representation of the location.

        Returns:
            String with location indicator and location ID
        """
        return f"Location({self.location_id})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the location.

        Returns:
            Same as __str__ method
        """
        return self.__str__()
