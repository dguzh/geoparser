import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature
    from geoparser.db.models.reference import Reference
    from geoparser.db.models.resolver import Resolver


class ReferentBase(SQLModel):
    """Base model for referent data."""


class Referent(ReferentBase, table=True):
    """
    Represents a resolved referent for a reference.

    A referent is a specific place in a gazetteer that a reference refers to.
    Each reference can have multiple potential referents, reflecting ambiguity in the text.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("reference.id", ondelete="CASCADE"), nullable=False
        )
    )
    feature_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("feature.id", ondelete="CASCADE"), nullable=False
        )
    )
    resolver_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("resolver.id", ondelete="CASCADE"), nullable=False
        )
    )
    reference: "Reference" = Relationship(back_populates="referents")
    resolver: "Resolver" = Relationship(
        back_populates="referents", sa_relationship_kwargs={"lazy": "joined"}
    )
    feature: "Feature" = Relationship(sa_relationship_kwargs={"lazy": "joined"})


class ReferentCreate(ReferentBase):
    """
    Model for creating a new referent.

    Includes the reference_id, feature_id, and resolver_id to associate the referent.
    """

    reference_id: uuid.UUID
    feature_id: int
    resolver_id: uuid.UUID


class ReferentUpdate(SQLModel):
    """Model for updating an existing referent."""

    id: uuid.UUID
    reference_id: t.Optional[uuid.UUID] = None
    feature_id: t.Optional[int] = None
    resolver_id: t.Optional[uuid.UUID] = None
