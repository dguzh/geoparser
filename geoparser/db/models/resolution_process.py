import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.toponym import Toponym
    from geoparser.db.models.resolution_module import ResolutionModule


class ResolutionProcessBase(SQLModel):
    """
    Base model for resolution process data.

    Records that a toponym was processed by a specific resolution module,
    regardless of whether any locations were found.
    """

    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    module_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolutionmodule.id", ondelete="CASCADE"), nullable=False
        )
    )


class ResolutionProcess(ResolutionProcessBase, table=True):
    """
    Represents a resolution process.

    Tracks that a toponym was processed by a specific resolution module,
    even if no locations were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym: "Toponym" = Relationship(back_populates="resolution_processes")
    module: "ResolutionModule" = Relationship(back_populates="resolution_processes")


class ResolutionProcessCreate(ResolutionProcessBase):
    """Model for creating a new resolution process record."""


class ResolutionProcessUpdate(SQLModel):
    """Model for updating an existing resolution process record."""

    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    module_id: t.Optional[uuid.UUID] = None 