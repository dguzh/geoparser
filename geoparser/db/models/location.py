import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.toponym import Toponym


class LocationBase(SQLModel):
    location_id: str  # ID of the location in the gazetteer
    resolution_module: str  # Name of the resolution module that identified this location
    confidence: t.Optional[float] = None  # Optional confidence score


class Location(LocationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    toponym_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("toponym.id", ondelete="CASCADE"), nullable=False
        )
    )
    toponym: "Toponym" = Relationship(back_populates="locations")


class LocationCreate(LocationBase):
    pass


class LocationUpdate(SQLModel):
    id: uuid.UUID
    toponym_id: t.Optional[uuid.UUID] = None
    resolution_module: t.Optional[str] = None
    location_id: t.Optional[str] = None
    confidence: t.Optional[float] = None 