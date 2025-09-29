import typing as t
from functools import cached_property

from shapely import wkb
from shapely.geometry.base import BaseGeometry
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

    @cached_property
    def data(self) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get the complete gazetteer row data for this feature.

        This property retrieves the data row from the gazetteer table
        and returns it as a dictionary. Results are cached automatically.

        Returns:
            Dictionary containing all columns from the gazetteer row, or None if not found
        """
        with Session(engine) as db:
            try:
                # Build query to get the complete row
                query = text(
                    f"SELECT * FROM {self.table_name} WHERE {self.identifier_name} = '{self.identifier_value}' ORDER BY rowid"
                )

                result = db.execute(query)
                row = result.fetchone()

                if row is None:
                    return None

                # Convert row to dictionary, exclude geometry, and return
                row_dict = dict(row._mapping)
                # Exclude geometry column from data as it's handled by the geometry property
                if "geometry" in row_dict:
                    del row_dict["geometry"]

                return row_dict

            except Exception:
                # Handle cases where table doesn't exist or query fails
                return None

    @cached_property
    def geometry(self) -> t.Optional[BaseGeometry]:
        """
        Get the geometry for this feature as a Shapely object.

        This property retrieves the geometry from the gazetteer table and
        converts it from WKB binary format to a Shapely geometry object.
        Results are cached automatically.

        Returns:
            Shapely geometry object, or None if no geometry exists for this feature
        """
        with Session(engine) as db:
            try:
                # Use SpatiaLite's AsBinary() to convert to standard WKB format
                query = text(
                    f"SELECT AsBinary(geometry) FROM {self.table_name} WHERE {self.identifier_name} = '{self.identifier_value}' ORDER BY rowid"
                )

                result = db.execute(query)
                row = result.fetchone()

                if row is None or row[0] is None:
                    return None

                # Convert WKB binary data to Shapely geometry
                return wkb.loads(row[0])

            except Exception:
                # Handle cases where geometry column doesn't exist or geometry data is corrupted
                return None


class FeatureCreate(FeatureBase):
    """Model for creating a new feature."""


class FeatureUpdate(SQLModel):
    """Model for updating an existing feature."""

    id: int
    gazetteer_name: t.Optional[str] = None
    table_name: t.Optional[str] = None
    identifier_name: t.Optional[str] = None
    identifier_value: t.Optional[str] = None
