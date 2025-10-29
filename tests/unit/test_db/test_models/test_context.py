"""
Unit tests for geoparser/db/models/context.py

Tests the Context model, including creation, validation, and relationships.
"""

import uuid

import pytest
from sqlmodel import Session

from geoparser.db.models import Context, ContextCreate, ContextUpdate


@pytest.mark.unit
class TestContextModel:
    """Test the Context model."""

    def test_creates_context_with_valid_data(
        self,
        test_session: Session,
        project_factory,
        recognizer_factory,
        resolver_factory,
    ):
        """Test that a Context can be created with valid data."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory()
        resolver = resolver_factory()
        context = Context(
            tag="test-tag",
            project_id=project.id,
            recognizer_id=recognizer.id,
            resolver_id=resolver.id,
        )

        # Act
        test_session.add(context)
        test_session.commit()
        test_session.refresh(context)

        # Assert
        assert context.id is not None
        assert isinstance(context.id, uuid.UUID)
        assert context.tag == "test-tag"
        assert context.project_id == project.id
        assert context.recognizer_id == recognizer.id
        assert context.resolver_id == resolver.id

    def test_generates_uuid_automatically(self, test_session: Session, project_factory):
        """Test that Context automatically generates a UUID for id."""
        # Arrange
        project = project_factory()
        context = Context(tag="test", project_id=project.id)

        # Act
        test_session.add(context)
        test_session.commit()

        # Assert
        assert context.id is not None
        assert isinstance(context.id, uuid.UUID)

    def test_allows_null_recognizer_and_resolver(
        self, test_session: Session, project_factory
    ):
        """Test that Context allows None for recognizer_id and resolver_id."""
        # Arrange
        project = project_factory()
        context = Context(
            tag="test", project_id=project.id, recognizer_id=None, resolver_id=None
        )

        # Act
        test_session.add(context)
        test_session.commit()
        test_session.refresh(context)

        # Assert
        assert context.recognizer_id is None
        assert context.resolver_id is None

    def test_enforces_unique_constraint_on_project_and_tag(
        self, test_session: Session, project_factory
    ):
        """Test that project_id and tag combination must be unique."""
        # Arrange
        project = project_factory()
        context1 = Context(tag="duplicate-tag", project_id=project.id)
        test_session.add(context1)
        test_session.commit()

        # Act & Assert
        context2 = Context(tag="duplicate-tag", project_id=project.id)
        test_session.add(context2)
        with pytest.raises(Exception):  # IntegrityError or similar
            test_session.commit()

    def test_allows_same_tag_for_different_projects(
        self, test_session: Session, project_factory
    ):
        """Test that the same tag can be used in different projects."""
        # Arrange
        project1 = project_factory()
        project2 = project_factory()
        context1 = Context(tag="same-tag", project_id=project1.id)
        context2 = Context(tag="same-tag", project_id=project2.id)

        # Act
        test_session.add(context1)
        test_session.add(context2)
        test_session.commit()
        test_session.refresh(context1)
        test_session.refresh(context2)

        # Assert
        assert context1.id != context2.id
        assert context1.tag == context2.tag
        assert context1.project_id != context2.project_id

    def test_has_project_relationship(self, test_session: Session, project_factory):
        """Test that Context has a relationship to Project."""
        # Arrange
        project = project_factory()
        context = Context(tag="test", project_id=project.id)
        test_session.add(context)
        test_session.commit()
        test_session.refresh(context)

        # Assert
        assert hasattr(context, "project")
        assert context.project is not None
        assert context.project.id == project.id

    def test_has_recognizer_relationship(
        self, test_session: Session, project_factory, recognizer_factory
    ):
        """Test that Context has a relationship to Recognizer."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory()
        context = Context(
            tag="test", project_id=project.id, recognizer_id=recognizer.id
        )
        test_session.add(context)
        test_session.commit()
        test_session.refresh(context)

        # Assert
        assert hasattr(context, "recognizer")
        assert context.recognizer is not None
        assert context.recognizer.id == recognizer.id

    def test_has_resolver_relationship(
        self, test_session: Session, project_factory, resolver_factory
    ):
        """Test that Context has a relationship to Resolver."""
        # Arrange
        project = project_factory()
        resolver = resolver_factory()
        context = Context(tag="test", project_id=project.id, resolver_id=resolver.id)
        test_session.add(context)
        test_session.commit()
        test_session.refresh(context)

        # Assert
        assert hasattr(context, "resolver")
        assert context.resolver is not None
        assert context.resolver.id == resolver.id

    def test_cascade_deletes_when_project_deleted(
        self, test_session: Session, project_factory
    ):
        """Test that deleting a project cascades to delete its contexts."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Context as ContextModel

        project = project_factory()
        context = Context(tag="test", project_id=project.id)
        test_session.add(context)
        test_session.commit()
        context_id = context.id

        # Act - Delete the project
        test_session.delete(project)
        test_session.commit()

        # Assert - Context should be deleted
        statement = select(ContextModel).where(ContextModel.id == context_id)
        result = test_session.exec(statement).first()
        assert result is None

    def test_sets_recognizer_to_null_when_recognizer_deleted(
        self, test_session: Session, project_factory, recognizer_factory
    ):
        """Test that deleting a recognizer sets recognizer_id to NULL in context."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Context as ContextModel

        project = project_factory()
        recognizer = recognizer_factory()
        context = Context(
            tag="test", project_id=project.id, recognizer_id=recognizer.id
        )
        test_session.add(context)
        test_session.commit()
        context_id = context.id

        # Act - Delete the recognizer
        test_session.delete(recognizer)
        test_session.commit()
        test_session.expire_all()  # Force session to reload from database

        # Assert - Context should still exist but recognizer_id should be NULL
        statement = select(ContextModel).where(ContextModel.id == context_id)
        result = test_session.exec(statement).first()
        assert result is not None
        assert result.recognizer_id is None

    def test_sets_resolver_to_null_when_resolver_deleted(
        self, test_session: Session, project_factory, resolver_factory
    ):
        """Test that deleting a resolver sets resolver_id to NULL in context."""
        # Arrange
        from sqlmodel import select

        from geoparser.db.models import Context as ContextModel

        project = project_factory()
        resolver = resolver_factory()
        context = Context(tag="test", project_id=project.id, resolver_id=resolver.id)
        test_session.add(context)
        test_session.commit()
        context_id = context.id

        # Act - Delete the resolver
        test_session.delete(resolver)
        test_session.commit()
        test_session.expire_all()  # Force session to reload from database

        # Assert - Context should still exist but resolver_id should be NULL
        statement = select(ContextModel).where(ContextModel.id == context_id)
        result = test_session.exec(statement).first()
        assert result is not None
        assert result.resolver_id is None


@pytest.mark.unit
class TestContextCreate:
    """Test the ContextCreate model."""

    def test_creates_with_required_fields(self, project_factory):
        """Test that ContextCreate can be created with required fields."""
        # Arrange
        project = project_factory()

        # Act
        context_create = ContextCreate(tag="test", project_id=project.id)

        # Assert
        assert context_create.tag == "test"
        assert context_create.project_id == project.id
        assert context_create.recognizer_id is None
        assert context_create.resolver_id is None

    def test_creates_with_all_fields(
        self, project_factory, recognizer_factory, resolver_factory
    ):
        """Test that ContextCreate can be created with all fields."""
        # Arrange
        project = project_factory()
        recognizer = recognizer_factory()
        resolver = resolver_factory()

        # Act
        context_create = ContextCreate(
            tag="test",
            project_id=project.id,
            recognizer_id=recognizer.id,
            resolver_id=resolver.id,
        )

        # Assert
        assert context_create.tag == "test"
        assert context_create.project_id == project.id
        assert context_create.recognizer_id == recognizer.id
        assert context_create.resolver_id == resolver.id


@pytest.mark.unit
class TestContextUpdate:
    """Test the ContextUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that ContextUpdate can be created with all fields."""
        # Act
        context_update = ContextUpdate(
            id=uuid.uuid4(),
            tag="new-tag",
            recognizer_id="rec-id",
            resolver_id="res-id",
        )

        # Assert
        assert context_update.id is not None
        assert context_update.tag == "new-tag"
        assert context_update.recognizer_id == "rec-id"
        assert context_update.resolver_id == "res-id"

    def test_allows_optional_fields(self):
        """Test that ContextUpdate allows optional fields."""
        # Act
        context_update = ContextUpdate(id=uuid.uuid4())

        # Assert
        assert context_update.id is not None
        assert context_update.tag is None
        assert context_update.recognizer_id is None
        assert context_update.resolver_id is None

    def test_allows_partial_update(self):
        """Test that ContextUpdate allows updating only specific fields."""
        # Act
        context_update = ContextUpdate(id=uuid.uuid4(), recognizer_id="new-rec")

        # Assert
        assert context_update.recognizer_id == "new-rec"
        assert context_update.resolver_id is None
        assert context_update.tag is None
