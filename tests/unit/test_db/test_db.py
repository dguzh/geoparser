"""
Unit tests for database configuration and test fixtures.

Tests the database setup following SQLAlchemy best practices and
test fixtures that redirect database operations to test databases.
"""

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, text


@pytest.mark.unit
class TestTestEngineFixture:
    """Test the test_engine fixture (configured like production)."""

    def test_provides_engine(self, test_engine):
        """Test that test_engine fixture provides an engine."""
        assert isinstance(test_engine, Engine)
        assert ":memory:" in str(test_engine.url)

    def test_enables_foreign_keys(self, test_session):
        """Test that foreign keys are enabled via global event listener."""
        result = test_session.exec(text("PRAGMA foreign_keys"))
        foreign_keys_enabled = result.scalar()
        assert foreign_keys_enabled == 1

    def test_loads_spatialite(self, test_session):
        """Test that SpatiaLite extension is loaded via global event listener."""
        result = test_session.exec(text("SELECT spatialite_version()"))
        version = result.scalar()
        assert version is not None
        assert isinstance(version, str)

    def test_creates_tables(self, test_session):
        """Test that tables are created automatically."""
        result = test_session.exec(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='project'")
        )
        table_name = result.scalar()
        assert table_name == "project"


@pytest.mark.unit
class TestTestSessionFixture:
    """Test the test_session fixture."""

    def test_provides_session(self, test_session):
        """Test that test_session fixture provides a session."""
        assert isinstance(test_session, Session)

    def test_uses_real_get_session(self, test_session):
        """Test that test_session uses the real get_session() function."""
        # The test_session fixture uses get_session() which automatically
        # uses the test database thanks to the patch_db fixture
        # This ensures we're testing the actual production code path

        # Create a simple record to verify the session works
        from geoparser.db.crud import ProjectRepository
        from geoparser.db.models import ProjectCreate

        project_create = ProjectCreate(name="test_project")
        project = ProjectRepository.create(test_session, project_create)

        assert project.name == "test_project"
        assert project.id is not None


@pytest.mark.unit
class TestPatchDbFixture:
    """Test the patch_db autouse fixture."""

    def test_redirects_engine_access(self, test_engine):
        """Test that accessing engine from db.db uses test engine."""
        from geoparser.db.db import engine

        # The autouse patch_db fixture should redirect this to test_engine
        assert ":memory:" in str(engine.url)

    def test_redirects_get_session(self, test_session):
        """Test that get_session() uses test database."""
        from geoparser.db.db import get_session

        # get_session() should use the test database
        with get_session() as session:
            result = session.exec(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='project'"
                )
            )
            table_name = result.scalar()
            assert table_name == "project"
