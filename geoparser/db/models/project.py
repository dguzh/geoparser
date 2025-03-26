import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document


class ProjectBase(SQLModel):
    """Base model for project data."""

    name: str = Field(index=True)


class Project(ProjectBase, table=True):
    """
    Represents a processing project.

    A project groups together related documents for processing.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    documents: list["Document"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ProjectCreate(ProjectBase):
    """Model for creating a new project."""


class ProjectUpdate(SQLModel):
    """Model for updating an existing project."""

    id: uuid.UUID
    name: t.Optional[str] = None
