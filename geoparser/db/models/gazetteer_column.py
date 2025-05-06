import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.gazetteer_relationship import GazetteerRelationship
    from geoparser.db.models.gazetteer_table import GazetteerTable


class GazetteerColumnBase(SQLModel):
    """Base model for gazetteer column metadata."""

    name: str = Field(index=True)


class GazetteerColumn(GazetteerColumnBase, table=True):
    """
    Represents a column belonging to a gazetteer table in the database.

    This stores metadata about columns in tables created for a gazetteer,
    allowing for more detailed querying and relationship tracking.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    table_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("gazetteertable.id", ondelete="CASCADE"), nullable=False
        )
    )
    table: "GazetteerTable" = Relationship(back_populates="columns")

    # Relationships for when this column is used in relationships
    local_relationships: list["GazetteerRelationship"] = Relationship(
        back_populates="local_column",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "foreign_keys": "[GazetteerRelationship.local_column_id]",
        },
    )

    remote_relationships: list["GazetteerRelationship"] = Relationship(
        back_populates="remote_column",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "foreign_keys": "[GazetteerRelationship.remote_column_id]",
        },
    )


class GazetteerColumnCreate(GazetteerColumnBase):
    """Model for creating a new gazetteer column record."""

    table_id: uuid.UUID


class GazetteerColumnUpdate(SQLModel):
    """Model for updating an existing gazetteer column record."""

    id: uuid.UUID
    name: t.Optional[str] = None
    table_id: t.Optional[uuid.UUID] = None
