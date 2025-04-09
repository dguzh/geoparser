import hashlib
import json

import pytest

from geoparser.modules.interfaces import (
    AbstractModule,
    AbstractRecognitionModule,
    AbstractResolutionModule,
)


def test_base_module_init():
    """Test initialization of AbstractModule with proper NAME attribute."""

    # Create a concrete subclass of AbstractModule with a NAME
    class TestModule(AbstractModule):
        NAME = "test_module"

    # Initialize with no config
    module = TestModule()
    assert module.name == "test_module"
    assert module.config == {}

    # Initialize with config
    config = {"param1": "value1", "param2": 42}
    module = TestModule(config=config)
    assert module.name == "test_module"
    assert module.config == config


def test_base_module_init_missing_name():
    """Test initialization of AbstractModule fails when NAME is not defined."""

    # Create a concrete subclass of AbstractModule without a NAME
    class InvalidModule(AbstractModule):
        pass

    # Initialize should raise ValueError
    with pytest.raises(ValueError, match="Module must define a NAME class attribute"):
        InvalidModule()


def test_base_module_str():
    """Test the string representation of a AbstractModule."""

    # Create a concrete subclass of AbstractModule with a NAME
    class TestModule(AbstractModule):
        NAME = "test_module"

    # Initialize with a config and check string representation
    config = {"param1": "value1", "param2": 42}
    module = TestModule(config=config)

    # Calculate expected config hash
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode("utf-8")).hexdigest()[:8]

    expected_str = f"<test_module (config={config_hash})>"
    assert str(module) == expected_str


def test_recognition_module_abstract():
    """Test that AbstractRecognitionModule is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidRecognitionModule(AbstractRecognitionModule):
        NAME = "invalid_recognition"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_toponyms"):
        InvalidRecognitionModule()


def test_recognition_module_implementation():
    """Test a valid implementation of AbstractRecognitionModule."""

    # Create a valid implementation
    class ValidRecognitionModule(AbstractRecognitionModule):
        NAME = "valid_recognition"

        def predict_toponyms(self, document_texts):
            return [[(0, 5), (10, 15)] for _ in document_texts]

    # Should instantiate without errors
    module = ValidRecognitionModule()
    assert module.name == "valid_recognition"

    # Should produce expected output
    documents = ["Test document 1", "Test document 2"]
    result = module.predict_toponyms(documents)
    assert len(result) == 2
    assert result[0] == [(0, 5), (10, 15)]
    assert result[1] == [(0, 5), (10, 15)]


def test_resolution_module_abstract():
    """Test that AbstractResolutionModule is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidResolutionModule(AbstractResolutionModule):
        NAME = "invalid_resolution"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_locations"):
        InvalidResolutionModule()


def test_resolution_module_implementation():
    """Test a valid implementation of AbstractResolutionModule."""

    # Create a valid implementation
    class ValidResolutionModule(AbstractResolutionModule):
        NAME = "valid_resolution"

        def predict_locations(self, toponym_data):
            return [[("loc1", 0.8), ("loc2", 0.6)] for _ in toponym_data]

    # Should instantiate without errors
    module = ValidResolutionModule()
    assert module.name == "valid_resolution"

    # Should produce expected output
    toponyms = [
        {"start": 0, "end": 5, "document_text": "Test document 1", "text": "Test"},
        {"start": 10, "end": 15, "document_text": "Test document 2", "text": "docum"},
    ]
    result = module.predict_locations(toponyms)
    assert len(result) == 2
    assert result[0] == [("loc1", 0.8), ("loc2", 0.6)]
    assert result[1] == [("loc1", 0.8), ("loc2", 0.6)]
