"""
Tests for retrieving documents by id in chunks.

SQLite caps how many parameters one statement may bind, so a large id list is
split into chunks and the results are concatenated. Getting the chunking
arithmetic wrong loses documents from the middle of a long request while the
call still succeeds, and the project filter has to survive every chunk or one
project's request starts returning another's documents.
"""

import uuid

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from geoparser.db.crud.document import DocumentRepository
from geoparser.db.models import DocumentCreate, Project, ProjectCreate

CHUNK_SIZE = 500


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


def _project(session, name):
    """Persist a project and return it."""
    project = Project(**ProjectCreate(name=name).model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _documents(session, project, count):
    """Persist `count` documents in a project and return their ids."""
    return [
        DocumentRepository.create(
            session, DocumentCreate(text=f"doc {index}", project_id=project.id)
        ).id
        for index in range(count)
    ]


@pytest.mark.unit
class TestChunking:
    """Requests that span more than one chunk."""

    def test_a_request_larger_than_one_chunk_returns_every_document(self, session):
        """
        All 501 documents come back, not just the first chunk.

        One over the chunk size is the smallest request that needs a second
        pass, so it is where an off-by-one in the chunk arithmetic shows.
        """
        # Arrange
        project = _project(session, "big")
        ids = _documents(session, project, CHUNK_SIZE + 1)

        # Act
        found = DocumentRepository.get_by_ids(session, project.id, ids)

        # Assert
        assert {document.id for document in found} == set(ids)

    def test_the_second_chunk_starts_where_the_first_ended(self, session):
        """
        No document is fetched twice and none is skipped.

        A chunk offset that restarted from zero, or stepped by the wrong
        amount, would return duplicates or a gap rather than an error.
        """
        # Arrange
        project = _project(session, "big")
        ids = _documents(session, project, CHUNK_SIZE + 3)

        # Act
        found = DocumentRepository.get_by_ids(session, project.id, ids)

        # Assert
        returned = [document.id for document in found]
        assert len(returned) == len(set(returned)) == CHUNK_SIZE + 3

    def test_a_request_that_fits_in_one_chunk_is_unaffected(self, session):
        """The common small case still works."""
        # Arrange
        project = _project(session, "small")
        ids = _documents(session, project, 3)

        # Act
        found = DocumentRepository.get_by_ids(session, project.id, ids)

        # Assert
        assert {document.id for document in found} == set(ids)

    def test_no_ids_means_no_query_and_no_documents(self, session):
        """An empty request returns nothing rather than everything."""
        # Arrange
        project = _project(session, "empty")
        _documents(session, project, 2)

        # Act & Assert
        assert DocumentRepository.get_by_ids(session, project.id, []) == []


@pytest.mark.unit
class TestScoping:
    """Which documents a request is allowed to see."""

    def test_another_projects_document_is_not_returned(self, session):
        """The project filter holds even when the id is known."""
        # Arrange
        mine = _project(session, "mine")
        theirs = _project(session, "theirs")
        (my_id,) = _documents(session, mine, 1)
        (their_id,) = _documents(session, theirs, 1)

        # Act
        found = DocumentRepository.get_by_ids(session, mine.id, [my_id, their_id])

        # Assert
        assert [document.id for document in found] == [my_id]

    def test_the_project_filter_survives_every_chunk(self, session):
        """
        A second chunk is scoped like the first.

        Building the filter once and reusing a stale statement, or dropping it
        on later passes, would leak documents only for large requests.
        """
        # Arrange
        mine = _project(session, "mine")
        theirs = _project(session, "theirs")
        my_ids = _documents(session, mine, CHUNK_SIZE + 1)
        their_ids = _documents(session, theirs, 2)

        # Act
        found = DocumentRepository.get_by_ids(session, mine.id, [*my_ids, *their_ids])

        # Assert
        assert {document.id for document in found} == set(my_ids)

    def test_an_unknown_id_is_ignored_rather_than_reported(self, session):
        """Missing ids are the caller's problem to notice, not an error here."""
        # Arrange
        project = _project(session, "mine")
        (known,) = _documents(session, project, 1)

        # Act
        found = DocumentRepository.get_by_ids(
            session, project.id, [known, uuid.uuid4()]
        )

        # Assert
        assert [document.id for document in found] == [known]
