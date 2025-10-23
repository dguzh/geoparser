"""
Unit tests for database engine setup and test fixtures.

Tests the production get_engine() function and test database fixtures.
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

    def test_enables_foreign_keys(self, test_engine):
        """Test that foreign keys are enabled."""
        with Session(test_engine) as test_db:
            result = test_db.exec(text("PRAGMA foreign_keys"))
            foreign_keys_enabled = result.scalar()
            assert foreign_keys_enabled == 1

    def test_loads_spatialite(self, test_engine):
        """Test that SpatiaLite extension is loaded."""
        with Session(test_engine) as test_db:
            result = test_db.exec(text("SELECT spatialite_version()"))
            version = result.scalar()
            assert version is not None
            assert isinstance(version, str)

    def test_creates_tables(self, test_engine):
        """Test that tables are created automatically."""
        with Session(test_engine) as test_db:
            result = test_db.exec(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='project'"
                )
            )
            table_name = result.scalar()
            assert table_name == "project"
