import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.reference import Reference
    from geoparser.db.models.resolver import Resolver


class ResolutionBase(SQLModel):
    """Base model for resolution data."""

    reference_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("reference.id", ondelete="CASCADE"), nullable=False
        )
    )
    resolver_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolver.id", ondelete="CASCADE"), nullable=False
        )
    )


class Resolution(ResolutionBase, table=True):
    """
    Tracks which references have been processed by which resolvers.

    This allows tracking of which resolvers have already processed a reference,
    even if no locations were found.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference: "Reference" = Relationship(back_populates="resolutions")
    resolver: "Resolver" = Relationship(back_populates="resolutions")


class ResolutionCreate(ResolutionBase):
    """Model for creating a new resolution record."""


class ResolutionUpdate(SQLModel):
    """Model for updating an existing resolution record."""

    id: uuid.UUID
    reference_id: t.Optional[uuid.UUID] = None
    resolver_id: t.Optional[uuid.UUID] = None
