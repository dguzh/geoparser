"""
Unit tests for database configuration and test fixtures.

Tests the database setup following SQLAlchemy best practices and
test fixtures that redirect database operations to test databases.
"""

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, create_engine, text


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

    def test_redirects_get_connection(self, test_session):
        """Test that get_connection() uses test database."""
        from geoparser.db.db import get_connection

        # get_connection() should use the test database
        with get_connection() as connection:
            result = connection.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='project'"
                )
            )
            table_name = result.scalar()
            assert table_name == "project"


@pytest.mark.unit
class TestDatabaseCompatibilityCheck:
    """Test the legacy-database compatibility check in create_db_and_tables()."""

    @staticmethod
    def _make_engine():
        from sqlalchemy.pool import StaticPool

        return create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

    def test_raises_for_legacy_gazetteer_tables(self):
        """A database holding old gazetteer tables is rejected clearly."""
        from unittest.mock import patch

        import geoparser.db.db as db

        legacy_engine = self._make_engine()
        with legacy_engine.connect() as connection:
            connection.execute(
                text("CREATE TABLE gazetteer (id INTEGER PRIMARY KEY, name TEXT)")
            )
            connection.commit()

        with patch.object(db, "engine", legacy_engine):
            with pytest.raises(RuntimeError):
                db.create_db_and_tables()

    def test_raises_for_legacy_referent_layout(self):
        """A referent table without feature_identifier is rejected clearly."""
        from unittest.mock import patch

        import geoparser.db.db as db

        legacy_engine = self._make_engine()
        with legacy_engine.connect() as connection:
            connection.execute(
                text(
                    "CREATE TABLE referent "
                    "(id INTEGER PRIMARY KEY, feature_id INTEGER)"
                )
            )
            connection.commit()

        with patch.object(db, "engine", legacy_engine):
            with pytest.raises(RuntimeError):
                db.create_db_and_tables()

    def test_allows_fresh_database(self):
        """An empty database is fine and gets its tables created."""
        from unittest.mock import patch

        import geoparser.db.db as db

        fresh_engine = self._make_engine()
        with patch.object(db, "engine", fresh_engine):
            db.create_db_and_tables()

        with fresh_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='referent'"
                )
            )
            assert result.first() is not None

    def test_allows_current_database(self):
        """A current database layout is accepted."""
        import geoparser.db.db as db

        # The autouse patch_db fixture points db.engine at the test engine,
        # which already has the current tables from create_all().
        db.create_db_and_tables()


@pytest.mark.unit
class TestSetSqlitePragma:
    """Test the _set_sqlite_pragma event listener."""

    def test_enables_foreign_keys_on_connect(self, test_session):
        """Test that foreign key enforcement is switched on for connections."""
        result = test_session.exec(text("PRAGMA foreign_keys"))
        assert result.scalar() == 1

    def test_skips_non_sqlite_connections(self):
        """Test that non-SQLite connections are left unmodified."""
        from unittest.mock import Mock

        from geoparser.db.db import _set_sqlite_pragma

        connection = Mock()

        # Act - a non-sqlite3 connection should be ignored without error
        _set_sqlite_pragma(connection, None)

        # Assert
        connection.cursor.assert_not_called()
