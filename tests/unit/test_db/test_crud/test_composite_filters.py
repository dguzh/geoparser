"""
Tests for the repository lookups that filter on two columns at once.

Each of these narrows by a row's owner *and* by the module that produced it.
Dropping either half still returns rows that look right in a single-module
test, but starts returning another document's or another module's work as soon
as a project has more than one of either.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.db.crud.recognition import RecognitionRepository
from geoparser.db.crud.reference import ReferenceRepository
from geoparser.db.crud.resolution import ResolutionRepository
from geoparser.db.models import (
    Document,
    DocumentCreate,
    Project,
    ProjectCreate,
    RecognitionCreate,
    Recognizer,
    RecognizerCreate,
    ReferenceCreate,
    ResolutionCreate,
    Resolver,
    ResolverCreate,
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


def _add(session, instance):
    """Persist one row and return it refreshed."""
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


@pytest.fixture
def world(session):
    """Two documents, two references, and two modules of each kind."""
    project = _add(session, Project(**ProjectCreate(name="demo").model_dump()))
    documents = [
        _add(
            session,
            Document(**DocumentCreate(text=text, project_id=project.id).model_dump()),
        )
        for text in ("Paris and Berlin", "Rome and Milan")
    ]
    recognizers = [
        _add(
            session,
            Recognizer(**RecognizerCreate(id=id, name="R", config={}).model_dump()),
        )
        for id in ("rec-a", "rec-b")
    ]
    resolvers = [
        _add(
            session, Resolver(**ResolverCreate(id=id, name="S", config={}).model_dump())
        )
        for id in ("res-a", "res-b")
    ]
    references = [
        ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=0,
                end=5,
                document_id=document.id,
                recognizer_id=recognizers[0].id,
            ),
        )
        for document in documents
    ]
    return {
        "documents": documents,
        "recognizers": recognizers,
        "resolvers": resolvers,
        "references": references,
    }


@pytest.mark.unit
class TestRecognitionByDocumentAndRecognizer:
    """Which document a recognizer has already processed."""

    @pytest.fixture(autouse=True)
    def recognitions(self, session, world):
        """Every combination of the two documents and two recognizers."""
        for document in world["documents"]:
            for recognizer in world["recognizers"]:
                RecognitionRepository.create(
                    session,
                    RecognitionCreate(
                        document_id=document.id, recognizer_id=recognizer.id
                    ),
                )

    def test_matches_on_both_the_document_and_the_recognizer(self, session, world):
        """Exactly the one row for that pair comes back."""
        # Act
        found = RecognitionRepository.get_by_document_and_recognizer(
            session, world["documents"][0].id, world["recognizers"][1].id
        )

        # Assert
        assert found is not None
        assert (found.document_id, found.recognizer_id) == (
            world["documents"][0].id,
            world["recognizers"][1].id,
        )

    def test_ignores_the_same_recognizer_on_another_document(self, session, world):
        """The other document's row for the same recognizer is excluded."""
        # Act
        found = RecognitionRepository.get_by_document_and_recognizer(
            session, world["documents"][1].id, world["recognizers"][0].id
        )

        # Assert
        assert found is not None
        assert found.document_id == world["documents"][1].id


@pytest.mark.unit
class TestResolutionByReferenceAndResolver:
    """Which reference a resolver has already processed."""

    @pytest.fixture(autouse=True)
    def resolutions(self, session, world):
        """Every combination of the two references and two resolvers."""
        for reference in world["references"]:
            for resolver in world["resolvers"]:
                ResolutionRepository.create(
                    session,
                    ResolutionCreate(
                        reference_id=reference.id, resolver_id=resolver.id
                    ),
                )

    def test_matches_on_both_the_reference_and_the_resolver(self, session, world):
        """Exactly the one row for that pair comes back."""
        # Act
        found = ResolutionRepository.get_by_reference_and_resolver(
            session, world["references"][0].id, world["resolvers"][1].id
        )

        # Assert
        assert found is not None
        assert (found.reference_id, found.resolver_id) == (
            world["references"][0].id,
            world["resolvers"][1].id,
        )

    def test_ignores_the_same_resolver_on_another_reference(self, session, world):
        """The other reference's row for the same resolver is excluded."""
        # Act
        found = ResolutionRepository.get_by_reference_and_resolver(
            session, world["references"][1].id, world["resolvers"][0].id
        )

        # Assert
        assert found is not None
        assert found.reference_id == world["references"][1].id


@pytest.mark.unit
class TestUnprocessedReferences:
    """Which references a resolver has still to see."""

    def test_excludes_references_this_resolver_already_resolved(self, session, world):
        """A resolution for one reference removes it from the queue."""
        # Arrange
        ResolutionRepository.create(
            session,
            ResolutionCreate(
                reference_id=world["references"][0].id,
                resolver_id=world["resolvers"][0].id,
            ),
        )
        project_id = world["documents"][0].project_id

        # Act
        pending = ResolutionRepository.get_unprocessed_references(
            session, project_id, world["resolvers"][0].id
        )

        # Assert
        assert [row.id for row in pending] == [world["references"][1].id]

    def test_another_resolvers_work_does_not_count(self, session, world):
        """A resolution by a different resolver leaves the reference pending."""
        # Arrange
        ResolutionRepository.create(
            session,
            ResolutionCreate(
                reference_id=world["references"][0].id,
                resolver_id=world["resolvers"][1].id,
            ),
        )
        project_id = world["documents"][0].project_id

        # Act
        pending = ResolutionRepository.get_unprocessed_references(
            session, project_id, world["resolvers"][0].id
        )

        # Assert
        assert {row.id for row in pending} == {
            world["references"][0].id,
            world["references"][1].id,
        }

    def test_references_in_another_project_are_not_returned(self, session, world):
        """The queue is scoped to the project that was asked for."""
        # Arrange - a second project with its own document and reference
        other_project = _add(
            session, Project(**ProjectCreate(name="other").model_dump())
        )
        other_document = _add(
            session,
            Document(
                **DocumentCreate(
                    text="Vienna", project_id=other_project.id
                ).model_dump()
            ),
        )
        ReferenceRepository.create(
            session,
            ReferenceCreate(
                start=0,
                end=6,
                document_id=other_document.id,
                recognizer_id=world["recognizers"][0].id,
            ),
        )

        # Act
        pending = ResolutionRepository.get_unprocessed_references(
            session, other_project.id, world["resolvers"][0].id
        )

        # Assert
        assert [row.document_id for row in pending] == [other_document.id]
