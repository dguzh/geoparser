import typing as t
import uuid

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from geoparser.annotator.db.models.toponym import Toponym


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
