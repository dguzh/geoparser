import typing as t
import uuid

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from geoparser.annotator.db.models.toponym import Toponym

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.session import Session


class DocumentBase(SQLModel):
    filename: str
    spacy_model: str
    spacy_applied: t.Optional[bool] = False
    text: str


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    doc_index: int
    session: t.Optional["Session"] = Relationship(back_populates="documents")
    toponyms: list[Toponym] = relationship(
        back_populates="document", order_by="desc(Toponym.start)"
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentGet(DocumentBase):
    id: uuid.UUID


class DocumentUpdate(DocumentGet):
    filename: t.Optional[str]
    spacy_model: t.Optional[str]
    spacy_applied: t.Optional[bool]
    text: t.Optional[str]
