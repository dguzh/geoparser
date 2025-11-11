import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.project import Project
    from geoparser.db.models.recognizer import Recognizer
    from geoparser.db.models.resolver import Resolver


class ContextBase(SQLModel):
    """Base model for context data."""

    tag: str


class Context(ContextBase, table=True):
    """
    Represents a tagged context within a project.

    A context record associates a tag with a specific recognizer and resolver
    combination within a project. This allows users to manage multiple result
    sets (e.g., from different pipeline runs or annotation sources) using
    human-friendly tags instead of module IDs.
    """

    __table_args__ = (UniqueConstraint("project_id", "tag"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        )
    )
    recognizer_id: t.Optional[str] = Field(
        default=None,
        sa_column=Column(
            String, ForeignKey("recognizer.id", ondelete="SET NULL"), nullable=True
        ),
    )
    resolver_id: t.Optional[str] = Field(
        default=None,
        sa_column=Column(
            String, ForeignKey("resolver.id", ondelete="SET NULL"), nullable=True
        ),
    )
    project: "Project" = Relationship()
    recognizer: t.Optional["Recognizer"] = Relationship()
    resolver: t.Optional["Resolver"] = Relationship()


class ContextCreate(ContextBase):
    """Model for creating a new context record."""

    project_id: uuid.UUID
    recognizer_id: t.Optional[str] = None
    resolver_id: t.Optional[str] = None


class ContextUpdate(SQLModel):
    """Model for updating an existing context record."""

    id: uuid.UUID
    tag: t.Optional[str] = None
    recognizer_id: t.Optional[str] = None
    resolver_id: t.Optional[str] = None
