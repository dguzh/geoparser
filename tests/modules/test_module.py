import pytest

from geoparser.modules.module import Module


def test_base_module_init(concrete_test_module_class):
    """Test initialization of Module with proper NAME attribute."""
    TestModule = concrete_test_module_class

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


def test_base_module_repr(concrete_test_module_class):
    """Test the representation of a Module."""
    TestModule = concrete_test_module_class

    # Initialize with config parameters and check representation
    module = TestModule(param1="value1", param2=42)

    # Expected string representation with parameters shown directly
    expected_str = "test_module(param1='value1', param2=42)"
    assert str(module) == expected_str
    assert repr(module) == expected_str


def test_config_order_invariance(concrete_test_module_class):
    """Test that different order of parameters produces the same config hash."""
    TestModule = concrete_test_module_class

    # Initialize with parameters in different orders
    module1 = TestModule(a=1, b=2)
    module2 = TestModule(b=2, a=1)

    # Representations should be identical due to sorted keys
    assert repr(module1) == repr(module2)


def test_config_set_not_allowed(concrete_test_module_class):
    """Test that sets are not allowed in config (must be JSON serializable)."""
    TestModule = concrete_test_module_class

    # Initialize with a set parameter should raise TypeError
    with pytest.raises(TypeError, match="not JSON serializable"):
        TestModule(features={"b", "a", "c"})


def test_config_normalization_mixed_types(concrete_test_module_class):
    """Test config normalization with mixed JSON-serializable parameter types."""
    TestModule = concrete_test_module_class

    # Initialize with mixed JSON-serializable types
    module = TestModule(
        string_param="test",
        int_param=42,
        list_param=[3, 1, 2],
        dict_param={"nested": "value"},
    )

    # Check normalization (keys are sorted alphabetically)
    expected_config = {
        "dict_param": {"nested": "value"},
        "int_param": 42,
        "list_param": [3, 1, 2],  # Lists are preserved as-is
        "string_param": "test",
    }
    assert module.config == expected_config
