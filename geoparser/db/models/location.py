import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature
    from geoparser.db.models.resolution_object import ResolutionObject
    from geoparser.db.models.toponym import Toponym


class LocationBase(SQLModel):
    """
    Base model for location data.

    Contains a reference to a feature in the gazetteer system.
    """


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
    feature_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("feature.id", ondelete="CASCADE"), nullable=False
        )
    )
    toponym: "Toponym" = Relationship(back_populates="locations")
    _feature: "Feature" = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    resolution_objects: list["ResolutionObject"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",
        },
    )

    @property
    def feature(self) -> t.Dict[str, t.Any]:
        """
        Get the feature data as a dictionary.

        Returns:
            Dictionary containing all columns from the gazetteer row
        """
        return self._feature.data

    def __str__(self) -> str:
        """
        Return a string representation of the location.

        Returns:
            String with location indicator
        """
        return (
            f"Location({self._feature.gazetteer_name}:{self._feature.identifier_value})"
        )

    def __repr__(self) -> str:
        """
        Return a developer representation of the location.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class LocationCreate(LocationBase):
    """
    Model for creating a new location.

    Includes the toponym_id and feature_id to associate the location.
    """

    toponym_id: uuid.UUID
    feature_id: uuid.UUID


class LocationUpdate(SQLModel):
    """Model for updating an existing location."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    feature_id: t.Optional[uuid.UUID] = None
