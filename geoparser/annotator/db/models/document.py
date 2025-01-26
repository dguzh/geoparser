import typing as t
import uuid

from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.session import Session
    from geoparser.annotator.db.models.toponym import Toponym, ToponymCreate


class DocumentBase(SQLModel):
    doc_index: t.Optional[int] = None
    filename: str
    spacy_model: str
    spacy_applied: t.Optional[bool] = False
    text: str


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="session.id")
    session: t.Optional["Session"] = Relationship(back_populates="documents")
    toponyms: list["Toponym"] = Relationship(back_populates="document")


class DocumentCreate(DocumentBase):
    toponyms: t.Optional[list["ToponymCreate"]] = []


class DocumentGet:
    id: uuid.UUID


class DocumentUpdate(DocumentGet):
    filename: t.Optional[str]
    spacy_model: t.Optional[str]
    spacy_applied: t.Optional[bool]
    text: t.Optional[str]
