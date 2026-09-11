"""
Tests for how a reference's cached text follows its span.

A reference stores the slice of document text it covers. Updating only one end
of the span has to keep the other, or the cached text silently stops matching
the offsets it claims to describe.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.db.crud.reference import ReferenceRepository
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Project,
    ProjectCreate,
    Recognizer,
    RecognizerCreate,
    ReferenceCreate,
    ReferenceUpdate,
)


@pytest.fixture
def session():
    """An in-memory database with the schema created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


@pytest.fixture
def reference(session):
    """A reference over "Paris and Berlin", covering "Paris"."""
    project = Project(**ProjectCreate(name="demo").model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)

    document = Document(
        **DocumentCreate(text="Paris and Berlin", project_id=project.id).model_dump()
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    recognizer = Recognizer(
        **RecognizerCreate(id="rec-1", name="TestRecognizer", config={}).model_dump()
    )
    session.add(recognizer)
    session.commit()

    return ReferenceRepository.create(
        session,
        ReferenceCreate(
            start=0, end=5, document_id=document.id, recognizer_id=recognizer.id
        ),
    )


@pytest.mark.unit
class TestReferenceText:
    """The cached slice of document text."""

    def test_create_stores_the_span_text(self, reference):
        """A new reference caches the text its offsets cover."""
        assert reference.text == "Paris"

    def test_moving_only_the_end_keeps_the_existing_start(self, session, reference):
        """
        A partial update falls back to the stored start.

        Losing that fallback would slice from the beginning of the document
        and cache text the reference does not actually cover.
        """
        # Act
        updated = ReferenceRepository.update(
            session,
            db_obj=reference,
            obj_in=ReferenceUpdate(id=reference.id, end=16),
        )

        # Assert
        assert (updated.start, updated.end) == (0, 16)
        assert updated.text == "Paris and Berlin"

    def test_moving_only_the_start_keeps_the_existing_end(self, session, reference):
        """The same fallback applies to the other end of the span."""
        # Act
        updated = ReferenceRepository.update(
            session,
            db_obj=reference,
            obj_in=ReferenceUpdate(id=reference.id, start=1),
        )

        # Assert
        assert (updated.start, updated.end) == (1, 5)
        assert updated.text == "aris"

    def test_moving_both_ends_re_slices_the_text(self, session, reference):
        """A full span update caches the new slice."""
        # Act
        updated = ReferenceRepository.update(
            session,
            db_obj=reference,
            obj_in=ReferenceUpdate(id=reference.id, start=10, end=16),
        )

        # Assert
        assert updated.text == "Berlin"


@pytest.mark.unit
class TestGetByDocumentAndSpan:
    """Looking a reference up by its exact span."""

    def test_finds_the_reference_at_that_span(self, session, reference):
        """An exact start/end match returns the reference."""
        # Act
        found = ReferenceRepository.get_by_document_and_span(
            session, reference.document_id, 0, 5
        )

        # Assert
        assert found is not None
        assert found.id == reference.id

    @pytest.mark.parametrize(("start", "end"), [(0, 4), (1, 5), (10, 16)])
    def test_returns_nothing_for_a_different_span(self, session, reference, start, end):
        """Both ends must match; a near miss is not a hit."""
        # Act & Assert
        assert (
            ReferenceRepository.get_by_document_and_span(
                session, reference.document_id, start, end
            )
            is None
        )
