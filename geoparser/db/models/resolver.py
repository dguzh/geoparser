import typing as t

from sqlmodel import JSON, Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.referent import Referent
    from geoparser.db.models.resolution import Resolution


class ResolverBase(SQLModel):
    """Base model for resolver metadata."""

    name: str = Field(index=True)
    config: t.Dict[str, t.Any] = Field(default_factory=dict, sa_type=JSON)


class Resolver(ResolverBase, table=True):
    """
    Stores metadata about resolvers.

    This includes configuration information and other details about specific
    resolver instances.
    """

    id: str = Field(primary_key=True)
    referents: list["Referent"] = Relationship(
        back_populates="resolver",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    resolutions: list["Resolution"] = Relationship(
        back_populates="resolver",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        """
        Return a string representation of the resolver.

        Returns:
            String with resolver name and config parameters
        """
        config_str = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())
        return f"{self.name}({config_str})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the resolver.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class ResolverCreate(ResolverBase):
    """Model for creating a new resolver record."""

    id: str


class ResolverUpdate(SQLModel):
    """Model for updating a resolver record."""

    id: str
    name: t.Optional[str] = None
    config: t.Optional[t.Dict[str, t.Any]] = None
