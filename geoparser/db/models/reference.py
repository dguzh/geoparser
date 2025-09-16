import typing as t
import uuid

from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.document import Document
    from geoparser.db.models.recognizer import Recognizer
    from geoparser.db.models.referent import Referent
    from geoparser.db.models.resolution import Resolution


class ReferenceBase(SQLModel):
    """Base model for reference data."""

    start: int  # Start position of the reference in the document text
    end: int  # End position of the reference in the document text
    text: t.Optional[str] = None  # The actual text of the reference


class Reference(ReferenceBase, table=True):
    """
    Represents a reference (place name) identified in a document.

    A reference is a place name found in text, defined by its start and end positions.
    It can have multiple potential referent interpretations (resolved referents).
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("document.id", ondelete="CASCADE"), nullable=False
        )
    )
    recognizer_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("recognizer.id", ondelete="CASCADE"), nullable=False
        )
    )
    document: "Document" = Relationship(back_populates="references")
    recognizer: "Recognizer" = Relationship(
        back_populates="references", sa_relationship_kwargs={"lazy": "joined"}
    )
    referents: list["Referent"] = Relationship(
        back_populates="reference",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",  # Enable eager loading
        },
    )
    resolutions: list["Resolution"] = Relationship(
        back_populates="reference",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        """
        Return a string representation of the reference.

        Returns:
            String with reference indicator and text content
        """
        return f'Reference("{self.text}")'

    def __repr__(self) -> str:
        """
        Return a developer representation of the reference.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class ReferenceCreate(ReferenceBase):
    """
    Model for creating a new reference.

    Includes the document_id and recognizer_id to associate the reference.
    """

    document_id: uuid.UUID
    recognizer_id: uuid.UUID


class ReferenceUpdate(SQLModel):
    """Model for updating an existing reference."""

    id: uuid.UUID
    document_id: t.Optional[uuid.UUID] = None
    recognizer_id: t.Optional[uuid.UUID] = None
    start: t.Optional[int] = None
    end: t.Optional[int] = None
