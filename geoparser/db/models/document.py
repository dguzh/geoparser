import typing as t
import uuid

from pydantic import AfterValidator
from sqlalchemy import UUID, Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from geoparser.db.models.validators import normalize_newlines

if t.TYPE_CHECKING:
    from geoparser.db.models.project import Project
    from geoparser.db.models.recognition_subject import RecognitionSubject
    from geoparser.db.models.reference import Reference


class DocumentBase(SQLModel):
    """
    Base model for document data.

    Contains the core text content of a document.
    """

    text: t.Annotated[str, AfterValidator(normalize_newlines)]


class Document(DocumentBase, table=True):
    """
    Represents a document to be processed for reference recognition and resolution.

    A document belongs to a project and can contain multiple references.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(
        sa_column=Column(
            UUID, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
        )
    )
    project: "Project" = Relationship(back_populates="documents")
    references: list["Reference"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={
            "order_by": "Reference.start",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "joined",  # Enable eager loading
        },
    )
    recognition_subjects: list["RecognitionSubject"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        """
        Return a string representation of the document.

        Returns:
            String with document indicator and text content
        """
        return f'Document("{self.text}")'

    def __repr__(self) -> str:
        """
        Return a developer representation of the document.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class DocumentCreate(DocumentBase):
    """
    Model for creating a new document.

    Includes the project_id to associate the document with a project.
    """

    project_id: uuid.UUID


class DocumentUpdate(SQLModel):
    """Model for updating an existing document."""

    id: uuid.UUID
    project_id: t.Optional[uuid.UUID] = None
    text: t.Optional[str] = None
