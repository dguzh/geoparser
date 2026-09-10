"""
Smoke tests for the annotator web application.

``geoparser/annotator/`` is omitted from coverage measurement, which in
practice meant it had no direct tests at all. These cover the wiring a type
checker cannot: that the app builds and serves, and that the repository
entry points behave when their optional arguments are simply left out.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.annotator.app import app
from geoparser.annotator.db.crud.document import DocumentRepository
from geoparser.annotator.db.models import (
    AnnotatorDocumentCreate,
    AnnotatorSession,
)


@pytest.fixture
def annotator_db():
    """An in-memory database with the annotator tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.unit
class TestAnnotatorApp:
    """The application object itself."""

    def test_serves_the_index_page(self):
        """The app builds and the index route renders."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200

    def test_openapi_schema_generates(self):
        """Every route's annotations are ones FastAPI can build a schema from."""
        # Act
        schema = app.openapi()

        # Assert
        assert schema["paths"]


@pytest.mark.unit
class TestDocumentRepositoryDefaults:
    """Optional repository arguments may be omitted."""

    def test_create_without_exclude_or_additional_extras(self, annotator_db):
        """
        Creating a document without passing `exclude` works.

        The repository merges its own exclusions with the caller's; with no
        caller-supplied list this must not try to unpack None.
        """
        # Arrange
        session_row = AnnotatorSession(gazetteer="geonames")
        annotator_db.add(session_row)
        annotator_db.commit()
        annotator_db.refresh(session_row)

        # Act
        document = DocumentRepository.create(
            annotator_db,
            AnnotatorDocumentCreate(
                filename="chapter.txt",
                spacy_model="en_core_web_sm",
                text="Paris is a city.",
            ),
            additional={"session_id": session_row.id},
        )

        # Assert
        assert document.filename == "chapter.txt"
        assert document.session_id == session_row.id
        assert document.doc_index == 0
