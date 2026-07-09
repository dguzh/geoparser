import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.reference import Reference
    from geoparser.db.models.resolver import Resolver
    from geoparser.gazetteer.feature import Feature


class ReferentBase(SQLModel):
    """Base model for referent data."""

    gazetteer_name: str
    feature_identifier: str


class Referent(ReferentBase, table=True):
    """
    Represents a resolved referent for a reference.

    A referent is a specific place in a gazetteer that a reference refers to,
    stored as a (gazetteer name, feature identifier) pair pointing into the
    gazetteer's installed artifact. Each reference can have multiple potential
    referents, reflecting ambiguity in the text.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    reference_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("reference.id", ondelete="CASCADE"), nullable=False
        )
    )
    resolver_id: str = Field(
        sa_column=Column(
            String, ForeignKey("resolver.id", ondelete="CASCADE"), nullable=False
        )
    )
    reference: "Reference" = Relationship(back_populates="referents")
    resolver: "Resolver" = Relationship(
        back_populates="referents", sa_relationship_kwargs={"lazy": "joined"}
    )

    @property
    def feature(self) -> t.Optional["Feature"]:
        """
        The gazetteer feature this referent points to.

        Returns:
            Feature object from the installed gazetteer, or None if the
            feature no longer exists in the gazetteer

        Raises:
            ValueError: If the referent's gazetteer is not installed
        """
        # Lazy import to avoid circular dependency
        from geoparser.gazetteer.gazetteer import Gazetteer

        return Gazetteer(self.gazetteer_name).find(self.feature_identifier)


class ReferentCreate(ReferentBase):
    """
    Model for creating a new referent.

    Includes the reference_id and resolver_id to associate the referent.
    """

    reference_id: uuid.UUID
    resolver_id: str


class ReferentUpdate(SQLModel):
    """Model for updating an existing referent."""

    id: uuid.UUID
    reference_id: t.Optional[uuid.UUID] = None
    gazetteer_name: t.Optional[str] = None
    feature_identifier: t.Optional[str] = None
    resolver_id: t.Optional[str] = None
