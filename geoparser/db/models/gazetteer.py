import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.source import Source


class GazetteerBase(SQLModel):
    """Base model for gazetteer data."""

    name: str = Field(index=True)


class Gazetteer(GazetteerBase, table=True):
    """
    Represents a gazetteer data source.

    A gazetteer is a geographical dictionary that provides location data.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    installed_at: t.Optional[datetime] = Field(default=None)
    sources: list["Source"] = Relationship(back_populates="gazetteer")


class GazetteerCreate(GazetteerBase):
    """Model for creating a new gazetteer."""


class GazetteerUpdate(SQLModel):
    """Model for updating an existing gazetteer."""

    id: uuid.UUID
    name: t.Optional[str] = None
    installed_at: t.Optional[datetime] = None
