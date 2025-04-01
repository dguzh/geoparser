import typing as t
import uuid

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.resolution_object import ResolutionObject
    from geoparser.db.models.resolution_subject import ResolutionSubject


class ResolutionModuleBase(SQLModel):
    """Base model for resolution module metadata."""

    config: t.Optional[dict] = Field(
        default=None, sa_type=JSON
    )  # Configuration as JSON which includes module_name


class ResolutionModule(ResolutionModuleBase, table=True):
    """
    Stores metadata about resolution modules.

    This includes configuration information and other details about specific
    resolution module instances. The module_name is stored in the config dictionary.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resolution_objects: list["ResolutionObject"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    resolution_subjects: list["ResolutionSubject"] = Relationship(
        back_populates="module",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ResolutionModuleCreate(ResolutionModuleBase):
    """Model for creating a new resolution module record."""


class ResolutionModuleUpdate(SQLModel):
    """Model for updating a resolution module record."""

    id: uuid.UUID
    config: t.Optional[dict] = None
