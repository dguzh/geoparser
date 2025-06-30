import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.referent import Referent
    from geoparser.db.models.resolution_module import ResolutionModule


class ResolutionObjectBase(SQLModel):
    """Base model for resolution object data."""

    referent_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("referent.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolutionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class ResolutionObject(ResolutionObjectBase, table=True):
    """
    Represents a resolution object.

    Tracks which resolution module identified a specific referent for a reference.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    referent: "Referent" = Relationship(back_populates="resolution_objects")
    module: "ResolutionModule" = Relationship(back_populates="resolution_objects")


class ResolutionObjectCreate(ResolutionObjectBase):
    """Model for creating a new resolution object."""


class ResolutionObjectUpdate(SQLModel):
    """Model for updating an existing resolution object."""

    id: uuid.UUID
    referent_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None
