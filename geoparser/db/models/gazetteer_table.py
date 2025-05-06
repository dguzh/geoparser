import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.gazetteer import Gazetteer
    from geoparser.db.models.gazetteer_relationship import GazetteerRelationship


class GazetteerTableBase(SQLModel):
    """Base model for gazetteer table metadata."""

    name: str = Field(index=True)
    table_name: str = Field(index=True)


class GazetteerTable(GazetteerTableBase, table=True):
    """
    Represents a table belonging to a gazetteer in the database.

    This stores metadata about tables created for a gazetteer,
    linking the physical table name to the source configuration
    that it was created from.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    gazetteer_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("gazetteer.id", ondelete="CASCADE"), nullable=False
        )
    )
    gazetteer: "Gazetteer" = Relationship(back_populates="tables")

    local_relationships: list["GazetteerRelationship"] = Relationship(
        back_populates="local_table",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "foreign_keys": "[GazetteerRelationship.local_table_id]",
        },
    )

    remote_relationships: list["GazetteerRelationship"] = Relationship(
        back_populates="remote_table",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "foreign_keys": "[GazetteerRelationship.remote_table_id]",
        },
    )


class GazetteerTableCreate(GazetteerTableBase):
    """Model for creating a new gazetteer table record."""

    gazetteer_id: uuid.UUID


class GazetteerTableUpdate(SQLModel):
    """Model for updating an existing gazetteer table record."""

    id: uuid.UUID
    name: t.Optional[str] = None
    table_name: t.Optional[str] = None
    gazetteer_id: t.Optional[uuid.UUID] = None
