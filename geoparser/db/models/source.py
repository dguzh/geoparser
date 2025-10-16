import typing as t
import uuid

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature
    from geoparser.db.models.gazetteer import Gazetteer


class SourceBase(SQLModel):
    """Base model for source data."""

    name: str = Field(index=True)
    location_id_name: str


class Source(SourceBase, table=True):
    """
    Represents a data source within a gazetteer.

    A source is a specific table or view within a gazetteer that contains
    geographic features. It stores the metadata about how features are
    identified in that source.
    """

    __table_args__ = (
        UniqueConstraint("gazetteer_id", "name", name="uq_source_gazetteer_name"),
    )

    id: int = Field(primary_key=True)
    gazetteer_id: uuid.UUID = Field(foreign_key="gazetteer.id", index=True)

    gazetteer: "Gazetteer" = Relationship(
        back_populates="sources", sa_relationship_kwargs={"lazy": "joined"}
    )
    features: list["Feature"] = Relationship(back_populates="source")

    def __str__(self) -> str:
        """
        Return a string representation of the source.

        Returns:
            String with source name
        """
        return f"Source({self.name})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the source.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class SourceCreate(SourceBase):
    """Model for creating a new source."""

    gazetteer_id: uuid.UUID


class SourceUpdate(SQLModel):
    """Model for updating an existing source."""

    id: int
    name: t.Optional[str] = None
    location_id_name: t.Optional[str] = None
    gazetteer_id: t.Optional[uuid.UUID] = None
