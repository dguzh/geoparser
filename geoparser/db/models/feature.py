import typing as t

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, Session, SQLModel, text

from geoparser.db.engine import engine

if t.TYPE_CHECKING:
    from geoparser.db.models.name import Name


class FeatureBase(SQLModel):
    """Base model for feature data."""

    gazetteer_name: str = Field(index=True)
    table_name: str
    identifier_name: str
    identifier_value: str


class Feature(FeatureBase, table=True):
    """
    Represents a feature from a gazetteer.

    A feature is a unique geographic entity in a gazetteer, identified by
    a specific identifier within that gazetteer's table structure.
    """

    __table_args__ = (
        UniqueConstraint(
            "gazetteer_name", "identifier_value", name="uq_feature_gazetteer_identifier"
        ),
    )

    id: int = Field(primary_key=True)
    names: list["Name"] = Relationship(
        back_populates="feature", sa_relationship_kwargs={"lazy": "joined"}
    )

    _data: t.Optional[t.Dict[str, t.Any]] = None

    @property
    def data(self) -> t.Dict[str, t.Any]:
        """
        Get the complete gazetteer row data for this feature.

        This property retrieves the full row from the original gazetteer table
        and returns it as a dictionary. Results are cached to avoid repeated
        database queries for the same feature.

        Returns:
            Dictionary containing all columns from the gazetteer row
        """
        if self._data is not None:
            return self._data

        with Session(engine) as db:
            # Build query to get the complete row
            query = text(
                f"SELECT * FROM {self.table_name} WHERE {self.identifier_name} = '{self.identifier_value}' ORDER BY rowid"
            )

            result = db.execute(query)
            row = result.fetchone()

            if row is None:
                raise ValueError(
                    f"Feature not found in table {self.table_name} "
                    f"with {self.identifier_name}={self.identifier_value}"
                )

            # Convert row to dictionary, cache it, and return
            self._data = dict(row._mapping)
            return self._data


class FeatureCreate(FeatureBase):
    """Model for creating a new feature."""


class FeatureUpdate(SQLModel):
    """Model for updating an existing feature."""

    id: int
    gazetteer_name: t.Optional[str] = None
    table_name: t.Optional[str] = None
    identifier_name: t.Optional[str] = None
    identifier_value: t.Optional[str] = None
