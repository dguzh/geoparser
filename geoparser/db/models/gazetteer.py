import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from geoparser.db.models.gazetteer_relationship import GazetteerRelationship
from geoparser.db.models.gazetteer_table import GazetteerTable


class GazetteerBase(SQLModel):
    """Base model for gazetteer data."""

    name: str = Field(index=True)
    modified: datetime = Field(default_factory=datetime.utcnow)


class Gazetteer(GazetteerBase, table=True):
    """
    Represents a gazetteer data source.

    A gazetteer is a geographical dictionary that provides location data.
    Each gazetteer's tables are prefixed in the database to emulate schemas.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tables: list["GazetteerTable"] = Relationship(
        back_populates="gazetteer",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    relationships: list["GazetteerRelationship"] = Relationship(
        back_populates="gazetteer",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class GazetteerCreate(GazetteerBase):
    """Model for creating a new gazetteer."""


class GazetteerUpdate(SQLModel):
    """Model for updating an existing gazetteer."""

    id: uuid.UUID
    name: t.Optional[str] = None
    modified: t.Optional[datetime] = None
