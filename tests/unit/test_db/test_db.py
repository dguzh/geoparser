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


@pytest.mark.unit
class TestSetSqlitePragma:
    """Test the _set_sqlite_pragma event listener."""

    def test_registers_soundex_function(self, test_session):
        """Test that the soundex function is registered on connections."""
        result = test_session.exec(text("SELECT soundex('Andorra')"))
        assert result.scalar() == "A536"

    def test_registers_levenshtein_function(self, test_session):
        """Test that the levenshtein function is registered on connections."""
        result = test_session.exec(text("SELECT levenshtein('Paris', 'Paris')"))
        assert result.scalar() == 0

    def test_skips_non_sqlite_connections(self):
        """Test that non-SQLite connections are left unmodified."""
        from unittest.mock import Mock

        from geoparser.db.db import _set_sqlite_pragma

        connection = Mock()

        # Act - a non-sqlite3 connection should be ignored without error
        _set_sqlite_pragma(connection, None)

        # Assert
        connection.cursor.assert_not_called()
        connection.create_function.assert_not_called()


@pytest.mark.unit
class TestOptimizedWrites:
    """Test the optimized_writes context manager and its PRAGMAs."""

    def test_enables_and_resets_flag(self):
        """Test that the flag is enabled within the context and reset after."""
        import geoparser.db.db as db

        assert db._optimized_writes_enabled is False
        with db.optimized_writes():
            assert db._optimized_writes_enabled is True
        assert db._optimized_writes_enabled is False

    def test_resets_flag_on_error(self):
        """Test that the flag is reset even when the context raises."""
        import geoparser.db.db as db

        with pytest.raises(ValueError):
            with db.optimized_writes():
                raise ValueError("boom")
        assert db._optimized_writes_enabled is False

    def test_applies_pragmas_when_enabled(self):
        """Test that throughput PRAGMAs are applied to connections when enabled."""
        import sqlite3

        from geoparser.db.db import _set_sqlite_pragma, optimized_writes

        connection = sqlite3.connect(":memory:")
        try:
            with optimized_writes():
                _set_sqlite_pragma(connection, None)

            cursor = connection.cursor()
            assert cursor.execute("PRAGMA synchronous").fetchone()[0] == 0
            assert cursor.execute("PRAGMA journal_mode").fetchone()[0] == "memory"
            assert cursor.execute("PRAGMA temp_store").fetchone()[0] == 2
            assert cursor.execute("PRAGMA cache_size").fetchone()[0] == -1048576
            cursor.close()
        finally:
            connection.close()

    def test_skips_pragmas_when_disabled(self):
        """Test that throughput PRAGMAs are not applied outside the context."""
        import sqlite3

        from geoparser.db.db import _set_sqlite_pragma

        connection = sqlite3.connect(":memory:")
        try:
            _set_sqlite_pragma(connection, None)

            cursor = connection.cursor()
            # Default synchronous is FULL (2), not OFF (0)
            assert cursor.execute("PRAGMA synchronous").fetchone()[0] == 2
            cursor.close()
        finally:
            connection.close()
