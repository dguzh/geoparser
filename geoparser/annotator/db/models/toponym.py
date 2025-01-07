import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import Document


class ToponymBase(SQLModel):
    text: str
    start: int
    end: int
    loc_id: t.Optional[str] = ""


class Toponym(ToponymBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document: t.Optional["Document"] = Relationship(back_populates="toponyms")


class ToponymCreate(ToponymBase):
    pass


class ToponymGet(ToponymBase):
    id: uuid.UUID
