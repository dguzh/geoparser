"""
Unit tests for geoparser/modules/module.py

Tests the Module base class, including ID generation, config handling,
and string representation.
"""

import hashlib

import pytest

from geoparser.modules.module import Module


# Create a concrete implementation for testing
class ConcreteModule(Module):
    """Concrete implementation of Module for testing purposes."""

    NAME = "TestModule"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


@pytest.mark.unit
class TestModuleInitialization:
    """Test Module initialization."""

    def test_requires_name_class_attribute(self):
        """Test that Module requires NAME class attribute to be defined."""

        # Arrange
        class NoNameModule(Module):
            NAME = None

        # Act & Assert
        with pytest.raises(
            ValueError, match="Module must define a NAME class attribute"
        ):
            NoNameModule()

    def test_sets_name_from_class_attribute(self):
        """Test that module name is set from NAME class attribute."""
        # Arrange & Act
        module = ConcreteModule()

        # Assert
        assert module.name == "TestModule"

    def test_stores_config_as_dict(self):
        """Test that config parameters are stored as a dictionary."""
        # Arrange & Act
        module = ConcreteModule(param1="value1", param2=42)

        # Assert
        assert isinstance(module.config, dict)
        assert module.config["param1"] == "value1"
        assert module.config["param2"] == 42

    def test_normalizes_config_through_json_round_trip(self):
        """Test that config is normalized via JSON serialization."""
        # Arrange & Act
        module = ConcreteModule(z_param="last", a_param="first", m_param="middle")

        # Assert - Keys should be sorted
        config_keys = list(module.config.keys())
        assert config_keys == ["a_param", "m_param", "z_param"]

    def test_accepts_empty_config(self):
        """Test that Module accepts no config parameters."""
        # Arrange & Act
        module = ConcreteModule()

        # Assert
        assert module.config == {}


@pytest.mark.unit
class TestModuleStringRepresentation:
    """Test Module string representations."""

    def test_str_includes_name_and_config(self):
        """Test that __str__ includes module name and config parameters."""
        # Arrange
        module = ConcreteModule(param1="value1", param2=42)

        # Act
        str_repr = str(module)

        # Assert
        assert "TestModule" in str_repr
        assert "param1" in str_repr
        assert "'value1'" in str_repr
        assert "param2" in str_repr
        assert "42" in str_repr

    def test_str_with_no_config(self):
        """Test that __str__ works correctly with no config parameters."""
        # Arrange
        module = ConcreteModule()

        # Act
        str_repr = str(module)

        # Assert
        assert str_repr == "TestModule()"

    def test_repr_matches_str(self):
        """Test that __repr__ returns the same as __str__."""
        # Arrange
        module = ConcreteModule(key="value")

        # Act & Assert
        assert repr(module) == str(module)


@pytest.mark.unit
class TestModuleIdGeneration:
    """Test Module ID generation."""

    def test_generates_deterministic_id(self):
        """Test that module ID is deterministic based on name and config."""
        # Arrange
        module1 = ConcreteModule(param="value")
        module2 = ConcreteModule(param="value")

        # Act
        id1 = module1.id
        id2 = module2.id

        # Assert - Same config should produce same ID
        assert id1 == id2

    def test_different_config_produces_different_id(self):
        """Test that different configurations produce different IDs."""
        # Arrange
        module1 = ConcreteModule(param="value1")
        module2 = ConcreteModule(param="value2")

        # Act
        id1 = module1.id
        id2 = module2.id

        # Assert - Different config should produce different ID
        assert id1 != id2

    def test_id_is_8_character_hash(self):
        """Test that module ID is 8 characters long."""
        # Arrange
        module = ConcreteModule(param="value")

        # Act
        module_id = module.id

        # Assert
        assert len(module_id) == 8
        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in module_id)

    def test_id_is_first_8_chars_of_sha256(self):
        """Test that ID is first 8 characters of SHA-256 hash of string representation."""
        # Arrange
        module = ConcreteModule(param="test")

        # Act
        module_id = module.id
        str_repr = str(module)
        expected_hash = hashlib.sha256(str_repr.encode()).hexdigest()[:8]

        # Assert
        assert module_id == expected_hash

    def test_id_consistent_across_multiple_calls(self):
        """Test that ID remains consistent across multiple calls."""
        # Arrange
        module = ConcreteModule(param="value")

        # Act
        id1 = module.id
        id2 = module.id
        id3 = module.id

        # Assert
        assert id1 == id2 == id3

    def test_empty_config_produces_valid_id(self):
        """Test that empty config still produces a valid ID."""
        # Arrange
        module = ConcreteModule()

        # Act
        module_id = module.id

        # Assert
        assert len(module_id) == 8
        assert isinstance(module_id, str)

    def test_config_order_affects_id(self):
        """Test that config parameter order doesn't affect ID (due to sorting)."""
        # Arrange
        # Create two modules with params in different order
        # (though JSON serialization sorts them)
        module1 = ConcreteModule(a="1", b="2", c="3")
        module2 = ConcreteModule(c="3", a="1", b="2")

        # Act
        id1 = module1.id
        id2 = module2.id

        # Assert - IDs should be the same because config is sorted
        assert id1 == id2
