import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class GazetteerBase(SQLModel):
    """Base model for gazetteer data."""

    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Gazetteer(GazetteerBase, table=True):
    """
    Represents a gazetteer data source.

    A gazetteer is a geographical dictionary that provides location data.
    Each gazetteer's tables are prefixed in the database to emulate schemas.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class GazetteerCreate(GazetteerBase):
    """Model for creating a new gazetteer."""


class GazetteerUpdate(SQLModel):
    """Model for updating an existing gazetteer."""

    id: uuid.UUID
    name: t.Optional[str] = None
