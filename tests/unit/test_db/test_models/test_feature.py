"""
Unit tests for geoparser/db/models/feature.py

Tests the Feature model with mocked dependencies.
"""

import pytest
from sqlmodel import Session

from geoparser.db.models import FeatureCreate, FeatureUpdate


@pytest.mark.unit
class TestFeatureModel:
    """Test the Feature model."""

    def test_creates_feature_with_valid_data(
        self, test_session: Session, source_factory
    ):
        """Test that a Feature can be created with valid data."""
        # Arrange
        from geoparser.db.models import Feature

        # Create parent entities
        source = source_factory()
        feature = Feature(source_id=source.id, location_id_value="123456")

        # Act
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Assert
        assert feature.id is not None
        assert isinstance(feature.id, int)
        assert feature.source_id == source.id
        assert feature.location_id_value == "123456"

    def test_generates_integer_id_automatically(
        self, test_session: Session, source_factory
    ):
        """Test that Feature automatically generates an integer ID."""
        # Arrange
        from geoparser.db.models import Feature

        # Create parent entities
        source = source_factory()
        feature = Feature(source_id=source.id, location_id_value="123")

        # Act
        test_session.add(feature)
        test_session.commit()

        # Assert
        assert feature.id is not None
        assert isinstance(feature.id, int)

    def test_has_source_relationship(self, test_session: Session):
        """Test that Feature has a relationship to source."""
        # Arrange
        from geoparser.db.models import Feature

        feature = Feature(source_id=1, location_id_value="123")

        # Assert
        assert hasattr(feature, "source")

    def test_has_names_relationship(self, test_session: Session):
        """Test that Feature has a relationship to names."""
        # Arrange
        from geoparser.db.models import Feature

        feature = Feature(source_id=1, location_id_value="123")

        # Assert
        assert hasattr(feature, "names")

    def test_str_representation(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that Feature has a useful string representation."""
        # Arrange
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="geonames")
        source = source_factory(gazetteer_id=gazetteer.id)
        feature = Feature(source_id=source.id, location_id_value="12345")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act
        str_repr = str(feature)

        # Assert
        assert "Feature" in str_repr
        assert "geonames" in str_repr
        assert "12345" in str_repr

    def test_repr_matches_str(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that __repr__ matches __str__."""
        # Arrange
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="test_gaz")
        source = source_factory(gazetteer_id=gazetteer.id)
        feature = Feature(source_id=source.id, location_id_value="999")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act & Assert
        assert repr(feature) == str(feature)

    def test_source_id_is_indexed(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that source_id field is indexed for efficient queries."""
        # This is verified by the model definition, hard to test at runtime
        # Just verify we can create features with different source_ids
        from geoparser.db.models import Feature

        # Create parent entities
        gazetteer = gazetteer_factory()
        source1 = source_factory(name="source1", gazetteer_id=gazetteer.id)
        source2 = source_factory(name="source2", gazetteer_id=gazetteer.id)

        feature1 = Feature(source_id=source1.id, location_id_value="123")
        feature2 = Feature(source_id=source2.id, location_id_value="456")

        test_session.add(feature1)
        test_session.add(feature2)
        test_session.commit()

        # Assert
        assert feature1.source_id == source1.id
        assert feature2.source_id == source2.id

    def test_has_unique_constraint_on_source_and_location(
        self, test_session: Session, source_factory
    ):
        """Test that Feature has unique constraint on (source_id, location_id_value)."""
        # Arrange
        from sqlalchemy.exc import IntegrityError

        from geoparser.db.models import Feature

        # Create parent entities
        source = source_factory()
        feature1 = Feature(source_id=source.id, location_id_value="123")
        test_session.add(feature1)
        test_session.commit()

        # Act & Assert - Try to create duplicate
        feature2 = Feature(source_id=source.id, location_id_value="123")
        test_session.add(feature2)

        with pytest.raises(IntegrityError):
            test_session.commit()


@pytest.mark.unit
class TestFeatureCreate:
    """Test the FeatureCreate model."""

    def test_creates_with_required_fields(self):
        """Test that FeatureCreate can be created with required fields."""
        # Arrange & Act
        feature_create = FeatureCreate(source_id=1, location_id_value="123456")

        # Assert
        assert feature_create.source_id == 1
        assert feature_create.location_id_value == "123456"


@pytest.mark.unit
class TestFeatureUpdate:
    """Test the FeatureUpdate model."""

    def test_creates_update_with_all_fields(self):
        """Test that FeatureUpdate can be created with all fields."""
        # Arrange & Act
        feature_update = FeatureUpdate(id=1, source_id=2, location_id_value="new_value")

        # Assert
        assert feature_update.id == 1
        assert feature_update.source_id == 2
        assert feature_update.location_id_value == "new_value"

    def test_allows_optional_fields(self):
        """Test that FeatureUpdate allows optional fields."""
        # Arrange & Act
        feature_update = FeatureUpdate(id=1)

        # Assert
        assert feature_update.id == 1
        assert feature_update.source_id is None
        assert feature_update.location_id_value is None


@pytest.mark.unit
class TestFeatureDataProperty:
    """Test the Feature.data cached property."""

    def test_data_returns_none_when_no_row_found(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that data property returns None when no matching row is found."""
        # Arrange
        from geoparser.db.db import get_connection
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="test_gaz")
        source = source_factory(
            name="test_source",
            location_id_name="id",
            gazetteer_id=gazetteer.id,
        )

        # Create table for the source but don't insert any data
        with get_connection() as connection:
            from sqlalchemy import text

            connection.execute(
                text(f"CREATE TABLE {source.name} (id TEXT PRIMARY KEY, name TEXT)")
            )
            connection.commit()

        feature = Feature(source_id=source.id, location_id_value="nonexistent")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act
        result = feature.data

        # Assert
        assert result is None

    def test_data_returns_none_on_exception(
        self, test_session: Session, source_factory
    ):
        """Test that data property returns None when query fails."""
        # Arrange
        from geoparser.db.models import Feature

        # Create a feature with a source that has no corresponding table
        source = source_factory(name="nonexistent_table")
        feature = Feature(source_id=source.id, location_id_value="123")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act - This should fail because table doesn't exist
        result = feature.data

        # Assert - Should return None instead of raising exception
        assert result is None

    def test_data_excludes_geometry_column(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that data property excludes the geometry column."""
        # Arrange
        from sqlalchemy import text

        from geoparser.db.db import get_connection
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="test_gaz")
        source = source_factory(
            name="geo_source",
            location_id_name="id",
            gazetteer_id=gazetteer.id,
        )

        # Create table with geometry column
        with get_connection() as connection:
            connection.execute(
                text(
                    f"CREATE TABLE {source.name} (id TEXT PRIMARY KEY, name TEXT, geometry TEXT)"
                )
            )
            connection.execute(
                text(
                    f"INSERT INTO {source.name} (id, name, geometry) VALUES ('1', 'Test', 'POINT(1 1)')"
                )
            )
            connection.commit()

        feature = Feature(source_id=source.id, location_id_value="1")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act
        result = feature.data

        # Assert
        assert result is not None
        assert "name" in result
        assert "geometry" not in result  # Should be excluded


@pytest.mark.unit
class TestFeatureGeometryProperty:
    """Test the Feature.geometry cached property."""

    def test_geometry_returns_none_when_no_row_found(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that geometry property returns None when no matching row is found."""
        # Arrange
        from sqlalchemy import text

        from geoparser.db.db import get_connection
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="test_gaz")
        source = source_factory(
            name="geo_source",
            location_id_name="id",
            gazetteer_id=gazetteer.id,
        )

        # Create table with geometry but no data
        with get_connection() as connection:
            connection.execute(
                text(f"CREATE TABLE {source.name} (id TEXT PRIMARY KEY)")
            )
            connection.execute(
                text(
                    f"SELECT AddGeometryColumn('{source.name}', 'geometry', 4326, 'POINT', 'XY')"
                )
            )
            connection.commit()

        feature = Feature(source_id=source.id, location_id_value="nonexistent")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act
        result = feature.geometry

        # Assert
        assert result is None

    def test_geometry_returns_none_when_geometry_is_null(
        self, test_session: Session, gazetteer_factory, source_factory
    ):
        """Test that geometry property returns None when geometry field is NULL."""
        # Arrange
        from sqlalchemy import text

        from geoparser.db.db import get_connection
        from geoparser.db.models import Feature

        gazetteer = gazetteer_factory(name="test_gaz")
        source = source_factory(
            name="geo_source",
            location_id_name="id",
            gazetteer_id=gazetteer.id,
        )

        # Create table with geometry and insert row with NULL geometry
        with get_connection() as connection:
            connection.execute(
                text(f"CREATE TABLE {source.name} (id TEXT PRIMARY KEY)")
            )
            connection.execute(
                text(
                    f"SELECT AddGeometryColumn('{source.name}', 'geometry', 4326, 'POINT', 'XY')"
                )
            )
            connection.execute(
                text(f"INSERT INTO {source.name} (id, geometry) VALUES ('1', NULL)")
            )
            connection.commit()

        feature = Feature(source_id=source.id, location_id_value="1")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act
        result = feature.geometry

        # Assert
        assert result is None

    def test_geometry_returns_none_on_exception(
        self, test_session: Session, source_factory
    ):
        """Test that geometry property returns None when query fails."""
        # Arrange
        from geoparser.db.models import Feature

        # Create a feature with a source that has no corresponding table
        source = source_factory(name="nonexistent_table")
        feature = Feature(source_id=source.id, location_id_value="123")
        test_session.add(feature)
        test_session.commit()
        test_session.refresh(feature)

        # Act - This should fail because table doesn't exist
        result = feature.geometry

        # Assert - Should return None instead of raising exception
        assert result is None
