import typing as t

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ToponymBase(SQLModel):
    """Base model for toponym data."""

    toponym: str = Field(index=True)
    feature_id: int = Field(foreign_key="feature.id", index=True)


class Toponym(ToponymBase, table=True):
    """
    Represents a toponym associated with a gazetteer feature.

    A toponym maps place names (strings) to feature IDs. Multiple toponyms can
    reference the same feature, and the same toponym can reference multiple features.
    """

    __table_args__ = (
        UniqueConstraint("toponym", "feature_id", name="uq_toponym_feature"),
    )

    id: int = Field(primary_key=True)


class ToponymCreate(ToponymBase):
    """Model for creating a new toponym."""


class ToponymUpdate(SQLModel):
    """Model for updating an existing toponym."""

    id: int
    toponym: t.Optional[str] = None
    feature_id: t.Optional[int] = None
