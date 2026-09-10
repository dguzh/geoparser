"""
Tests for the lazy re-exports of the ``geoparser.gazetteer`` package.

``GazetteerBuilder`` is resolved on first attribute access so that importing
the package for a lookup does not drag in the whole build pipeline. These
tests pin both that the export still works and that unknown names still fail
the way a normal module would.
"""

import pytest


@pytest.mark.unit
class TestLazyGazetteerExports:
    """The package exposes GazetteerBuilder without importing it eagerly."""

    def test_gazetteer_builder_resolves_on_access(self):
        """Accessing the attribute returns the real class."""
        # Arrange
        import geoparser.gazetteer as package

        # Act
        builder = package.GazetteerBuilder

        # Assert
        from geoparser.gazetteer.build import GazetteerBuilder

        assert builder is GazetteerBuilder

    def test_unknown_attribute_raises_attribute_error(self):
        """An unexported name fails like any other missing module attribute."""
        # Arrange
        import geoparser.gazetteer as package

        # Act & Assert
        with pytest.raises(AttributeError, match="has no attribute 'Nonexistent'"):
            _ = package.Nonexistent

    def test_build_pipeline_is_not_imported_by_the_package_itself(self):
        """Importing the package must not pull the build pipeline in with it."""
        # Arrange & Act - a fresh interpreter, so import order is not polluted
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import geoparser.gazetteer, sys; "
                "print('geoparser.gazetteer.build' in sys.modules)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Assert
        assert result.stdout.strip() == "False"
