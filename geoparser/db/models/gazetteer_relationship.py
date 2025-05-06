import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.gazetteer import Gazetteer
    from geoparser.db.models.gazetteer_table import GazetteerTable


class GazetteerRelationshipBase(SQLModel):
    """Base model for gazetteer relationship metadata."""

    local_column: str
    remote_column: str


class GazetteerRelationship(GazetteerRelationshipBase, table=True):
    """
    Represents a relationship between two tables in a gazetteer.

    This stores metadata about joins that can be used by resolution logic,
    without actually creating foreign key constraints in SQLite.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    gazetteer_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("gazetteer.id", ondelete="CASCADE"), nullable=False
        )
    )
    gazetteer: "Gazetteer" = Relationship(back_populates="relationships")

    local_table_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("gazetteertable.id", ondelete="CASCADE"), nullable=False
        )
    )
    local_table: "GazetteerTable" = Relationship(
        back_populates="local_relationships",
        sa_relationship_kwargs={
            "foreign_keys": "[GazetteerRelationship.local_table_id]"
        },
    )

    remote_table_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("gazetteertable.id", ondelete="CASCADE"), nullable=False
        )
    )
    remote_table: "GazetteerTable" = Relationship(
        back_populates="remote_relationships",
        sa_relationship_kwargs={
            "foreign_keys": "[GazetteerRelationship.remote_table_id]"
        },
    )


class GazetteerRelationshipCreate(GazetteerRelationshipBase):
    """Model for creating a new gazetteer relationship."""

    gazetteer_id: uuid.UUID
    local_table_id: uuid.UUID
    remote_table_id: uuid.UUID


class GazetteerRelationshipUpdate(SQLModel):
    """Model for updating an existing gazetteer relationship."""

    id: uuid.UUID
    gazetteer_id: t.Optional[uuid.UUID] = None
    local_table_id: t.Optional[uuid.UUID] = None
    local_column: t.Optional[str] = None
    remote_table_id: t.Optional[uuid.UUID] = None
    remote_column: t.Optional[str] = None
