import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.location import Location, LocationRead
    from geoparser.db.models.recognition_module import RecognitionModuleRead
    from geoparser.db.models.recognition_object import RecognitionObject
    from geoparser.db.models.resolution_subject import ResolutionSubject


class ToponymBase(SQLModel):
    """Base model for toponym data."""

    start: int  # Start position of the toponym in the document text
    end: int  # End position of the toponym in the document text
    text: t.Optional[str] = None  # The actual text of the toponym


class Toponym(ToponymBase, table=True):
    """
    Represents a toponym (place name) identified in a document.

    A toponym is a place name found in text, defined by its start and end positions.
    It can have multiple potential location interpretations (resolved locations).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "Document" = Relationship(back_populates="toponyms")
    locations: list["Location"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",  # Enable eager loading
        },
    )
    recognition_objects: list["RecognitionObject"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",
        },
    )
    resolution_subjects: list["ResolutionSubject"] = Relationship(
        back_populates="toponym",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


class ToponymCreate(ToponymBase):
    """
    Model for creating a new toponym.

    Includes the document_id to associate the toponym with a document.
    """

    document_id: uuid.UUID


class ToponymUpdate(SQLModel):
    """Model for updating an existing toponym."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None


class ToponymRead(SQLModel):
    """
    Model for reading toponym data.

    Only exposes the id, document_id, start, end, text and locations of a toponym.
    """

    id: uuid.UUID
    document_id: uuid.UUID
    start: int
    end: int
    text: t.Optional[str] = None
    locations: list["LocationRead"] = []
    modules: list["RecognitionModuleRead"] = []

    model_config = {"from_attributes": True}

    def __str__(self) -> str:
        """
        Return a string representation of the toponym.

        Returns:
            String with toponym indicator and text content
        """
        return f'Toponym("{self.text}")' if self.text else 'Toponym("<unnamed>")'

    def __repr__(self) -> str:
        """
        Return a developer representation of the toponym.

        Returns:
            Same as __str__ method
        """
        return self.__str__()
