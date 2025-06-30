import pytest

from geoparser.modules.module import Module
from geoparser.modules.recognizers.recognizer import Recognizer
from geoparser.modules.resolvers.resolver import Resolver


def test_base_module_init():
    """Test initialization of Module with proper NAME attribute."""

    # Create a concrete subclass of Module with a NAME
    class TestModule(Module):
        NAME = "test_module"

    # Initialize with no config
    module = TestModule()
    assert module.name == "test_module"
    assert module.config == {}

    # Initialize with config parameters
    module = TestModule(param1="value1", param2=42)
    assert module.name == "test_module"
    assert module.config == {"param1": "value1", "param2": 42}


def test_base_module_init_missing_name():
    """Test initialization of Module fails when NAME is not defined."""

    # Create a concrete subclass of Module without a NAME
    class InvalidModule(Module):
        pass

    # Initialize should raise ValueError
    with pytest.raises(ValueError, match="Module must define a NAME class attribute"):
        InvalidModule()


def test_base_module_repr():
    """Test the representation of a Module."""

    # Create a concrete subclass of Module with a NAME
    class TestModule(Module):
        NAME = "test_module"

    # Initialize with config parameters and check representation
    module = TestModule(param1="value1", param2=42)

    # Expected string representation with parameters shown directly
    expected_str = "test_module(param1='value1', param2=42)"
    assert str(module) == expected_str
    assert repr(module) == expected_str


def test_config_order_invariance():
    """Test that different order of parameters produces the same config hash."""

    # Create a concrete subclass of Module with a NAME
    class TestModule(Module):
        NAME = "test_module"

    # Initialize with parameters in different orders
    module1 = TestModule(a=1, b=2)
    module2 = TestModule(b=2, a=1)

    # Representations should be identical due to sorted keys
    assert repr(module1) == repr(module2)


def test_recognition_module_abstract():
    """Test that Recognizer is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidRecognitionModule(Recognizer):
        NAME = "invalid_recognition"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_references"):
        InvalidRecognitionModule()


def test_recognition_module_implementation():
    """Test a valid implementation of Recognizer with Document ORM objects."""

    # Create a valid implementation that works with Document ORM objects
    class ValidRecognitionModule(Recognizer):
        NAME = "valid_recognition"

        def predict_references(self, documents):
            return [[(0, 5), (10, 15)] for _ in documents]

    # Should instantiate without errors
    module = ValidRecognitionModule()
    assert module.name == "valid_recognition"

    # Should instantiate with parameters
    module = ValidRecognitionModule(custom_param="test")
    assert module.config == {"custom_param": "test"}

    # Should produce expected output with mock Document objects
    from unittest.mock import MagicMock

    # Create mock Document objects
    doc1 = MagicMock()
    doc1.text = "Test document 1"
    doc2 = MagicMock()
    doc2.text = "Test document 2"
    documents = [doc1, doc2]

    result = module.predict_references(documents)
    assert len(result) == 2
    assert result[0] == [(0, 5), (10, 15)]
    assert result[1] == [(0, 5), (10, 15)]


def test_resolution_module_abstract():
    """Test that Resolver is abstract and requires implementation."""

    # Create a concrete subclass that doesn't implement required methods
    class InvalidResolutionModule(Resolver):
        NAME = "invalid_resolution"

    # Should raise TypeError when instantiated due to abstract methods
    with pytest.raises(TypeError, match="predict_referents"):
        InvalidResolutionModule()


def test_resolution_module_implementation():
    """Test a valid implementation of Resolver with Reference ORM objects."""

    # Create a valid implementation that works with Reference ORM objects
    class ValidResolutionModule(Resolver):
        NAME = "valid_resolution"

        def predict_referents(self, references):
            return [
                [("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]
                for _ in references
            ]

    # Should instantiate without errors
    module = ValidResolutionModule()
    assert module.name == "valid_resolution"

    # Should instantiate with parameters
    module = ValidResolutionModule(model="test_model", threshold=0.5)
    assert module.config == {"model": "test_model", "threshold": 0.5}

    # Should produce expected output with mock Reference objects
    from unittest.mock import MagicMock

    # Create mock Reference objects with Document relationships
    ref1 = MagicMock()
    ref1.start = 0
    ref1.end = 5
    ref1.text = "Test"
    ref1.document.text = "Test document 1"

    ref2 = MagicMock()
    ref2.start = 10
    ref2.end = 15
    ref2.text = "docum"
    ref2.document.text = "Test document 2"

    references = [ref1, ref2]

    result = module.predict_referents(references)
    assert len(result) == 2
    assert result[0] == [("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]
    assert result[1] == [("test_gazetteer", "loc1"), ("test_gazetteer", "loc2")]
