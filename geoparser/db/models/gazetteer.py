import typing as t
import uuid

from sqlmodel import Field, SQLModel


class GazetteerBase(SQLModel):
    """Base model for gazetteer data."""

    name: str = Field(index=True)


class Gazetteer(GazetteerBase, table=True):
    """
    Represents a gazetteer data source.

    A gazetteer is a geographical dictionary that provides location data.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class GazetteerCreate(GazetteerBase):
    """Model for creating a new gazetteer."""


class GazetteerUpdate(SQLModel):
    """Model for updating an existing gazetteer."""

    id: uuid.UUID
    name: t.Optional[str] = None
