"""
Tests for how recognizer and resolver rows render their configuration.

The rendering is not only for humans: the module id is a hash of the same
string shape, so a row whose repr separates config entries differently reads
back as a different configuration than the module that wrote it.
"""

import pytest

from geoparser.db.models import Recognizer, Resolver
from geoparser.modules.module import Module


@pytest.mark.unit
class TestConfigRendering:
    """The separator between configuration entries."""

    @pytest.mark.parametrize("model", [Recognizer, Resolver])
    def test_entries_are_separated_by_a_comma_and_a_space(self, model):
        """Two config entries render as `a=1, b=2`."""
        # Arrange
        row = model(id="m-1", name="M", config={"a": 1, "b": 2})

        # Act & Assert
        assert str(row) == "M(a=1, b=2)"

    def test_a_module_renders_the_same_way_as_its_row(self):
        """The in-memory module and its database row agree on the string."""

        # Arrange
        class Example(Module):
            NAME = "M"

        module = Example(a=1, b=2)
        row = Recognizer(id=module.id, name=module.name, config=module.config)

        # Act & Assert
        assert str(module) == str(row)

    def test_a_module_without_a_name_is_rejected(self):
        """The NAME class attribute is required."""

        # Arrange
        class Nameless(Module):
            pass

        # Act & Assert
        with pytest.raises(ValueError):
            Nameless()
