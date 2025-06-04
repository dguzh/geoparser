import typing as t
import uuid

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class NameBase(SQLModel):
    """Base model for name data."""

    name: str = Field(index=True)
    feature_id: uuid.UUID = Field(foreign_key="feature.id", index=True)


class Name(NameBase, table=True):
    """
    Represents a name associated with a gazetteer feature.

    A name maps place names (strings) to feature IDs. Multiple names can
    reference the same feature, and the same name can reference multiple features.
    """

    __table_args__ = (UniqueConstraint("name", "feature_id", name="uq_name_feature"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class NameCreate(NameBase):
    """Model for creating a new name."""


class NameUpdate(SQLModel):
    """Model for updating an existing name."""

    id: uuid.UUID
    name: t.Optional[str] = None
    feature_id: t.Optional[uuid.UUID] = None
