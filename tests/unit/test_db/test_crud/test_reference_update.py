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


@pytest.mark.unit
class TestSpansThatDoNotStartAtZero:
    """
    The same slicing, for a reference that does not start at offset zero.

    A start of zero hides a whole class of mistake: ``text[None:end]`` and
    ``text[0:end]`` are the same string, so losing the start entirely still
    caches the right text. These use an offset span, where they differ.
    """

    def test_create_slices_from_the_start_offset(self, session, reference):
        """A reference later in the document caches only its own span."""
        # Act
        created = ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=10,
                end=16,
                document_id=reference.document_id,
                recognizer_id=reference.recognizer_id,
            ),
        )

        # Assert
        assert created.text == "Berlin"

    def test_moving_only_the_end_keeps_a_non_zero_start(self, session, reference):
        """The fallback start is the stored offset, not the start of the text."""
        # Arrange - a reference over "and"
        middle = ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=6,
                end=9,
                document_id=reference.document_id,
                recognizer_id=reference.recognizer_id,
            ),
        )

        # Act
        updated = ReferenceRepository.update(
            session,
            db_obj=middle,
            obj_in=ReferenceUpdate(id=middle.id, end=16),
        )

        # Assert
        assert (updated.start, updated.end) == (6, 16)
        assert updated.text == "and Berlin"


@pytest.mark.unit
class TestGetByDocument:
    """Listing a document's references."""

    def test_returns_only_the_references_of_that_document(self, session, reference):
        """References of a sibling document are not included."""
        # Arrange - a second document in the same project, with its own reference
        other = Document(
            **DocumentCreate(
                text="Rome and Milan",
                project_id=session.get(Document, reference.document_id).project_id,
            ).model_dump()
        )
        session.add(other)
        session.commit()
        session.refresh(other)
        ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=0,
                end=4,
                document_id=other.id,
                recognizer_id=reference.recognizer_id,
            ),
        )

        # Act
        found = ReferenceRepository.get_by_document(session, reference.document_id)

        # Assert
        assert [item.id for item in found] == [reference.id]


@pytest.mark.unit
class TestSpanLookupIsScopedToOneDocument:
    """The span lookup must not reach across documents."""

    def test_the_same_span_in_another_document_is_not_returned(
        self, session, reference
    ):
        """
        Two documents can hold a reference at the same offsets.

        Spans are only meaningful within a document, so dropping the document
        from the lookup returns whichever row happens to come first --
        plausible, and wrong.
        """
        # Arrange - a second document whose reference covers the same span
        original = session.get(Document, reference.document_id)
        other = Document(
            **DocumentCreate(
                text="Paris and Berlin", project_id=original.project_id
            ).model_dump()
        )
        session.add(other)
        session.commit()
        session.refresh(other)
        twin = ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=0,
                end=5,
                document_id=other.id,
                recognizer_id=reference.recognizer_id,
            ),
        )

        # Act
        found = ReferenceRepository.get_by_document_and_span(session, other.id, 0, 5)

        # Assert
        assert found is not None
        assert found.id == twin.id
        assert found.id != reference.id
