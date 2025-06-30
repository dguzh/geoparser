import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature
    from geoparser.db.models.reference import Reference
    from geoparser.db.models.resolution_object import ResolutionObject


class ReferentBase(SQLModel):
    """
    Base model for referent data.

    Contains a reference to a feature in the gazetteer system.
    """


class Referent(ReferentBase, table=True):
    """
    Represents a resolved referent for a reference.

    A referent is a specific place in a gazetteer that a reference refers to.
    Each reference can have multiple potential referents, reflecting ambiguity in the text.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("reference.id", ondelete="CASCADE"), nullable=False
        )
    )
    feature_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("feature.id", ondelete="CASCADE"), nullable=False
        )
    )
    reference: "Reference" = Relationship(back_populates="referents")
    _feature: "Feature" = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    resolution_objects: list["ResolutionObject"] = Relationship(
        back_populates="referent",
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
        Return a string representation of the referent.

        Returns:
            String with referent indicator
        """
        return (
            f"Referent({self._feature.gazetteer_name}:{self._feature.identifier_value})"
        )

    def __repr__(self) -> str:
        """
        Return a developer representation of the referent.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class ReferentCreate(ReferentBase):
    """
    Model for creating a new referent.

    Includes the reference_id and feature_id to associate the referent.
    """

    reference_id: uuid.UUID
    feature_id: int


class ReferentUpdate(SQLModel):
    """Model for updating an existing referent."""

    id: uuid.UUID
    reference_id: t.Optional[uuid.UUID] = None
    feature_id: t.Optional[int] = None
