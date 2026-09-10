import typing as t
import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from geoparser.annotator.db.models.settings import AnnotatorSessionSettingsCreate

if t.TYPE_CHECKING:
    from geoparser.annotator.db.models.document import (
        AnnotatorDocument,
        AnnotatorDocumentCreate,
    )
    from geoparser.annotator.db.models.settings import AnnotatorSessionSettings


class AnnotatorSessionBase(SQLModel):
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    gazetteer: str


class AnnotatorSession(AnnotatorSessionBase, table=True):
    __tablename__ = "annotatorsession"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    settings: "AnnotatorSessionSettings" = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    documents: list["AnnotatorDocument"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "order_by": "AnnotatorDocument.doc_index",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class AnnotatorSessionCreate(AnnotatorSessionBase):
    settings: "AnnotatorSessionSettingsCreate" = AnnotatorSessionSettingsCreate()
    documents: list["AnnotatorDocumentCreate"] | None = []


class AnnotatorSessionDownload(AnnotatorSessionBase):
    documents: list["AnnotatorDocumentCreate"] | None = []


class AnnotatorSessionForTemplate(AnnotatorSessionBase):
    id: uuid.UUID
    num_documents: int


class AnnotatorSessionUpdate(SQLModel):
    id: uuid.UUID
    created_at: datetime | None = None
    last_updated: datetime | None = None
    gazetteer: str | None = None
