"""
Unit tests for geoparser/gazetteer/installer/stages/view.py

Tests the ViewStage class.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SelectConfig,
    SourceConfig,
    SourceKind,
    ViewConfig,
)
from geoparser.gazetteer.installer.stages.view import ViewStage


def _build_source(with_view: bool) -> SourceConfig:
    view = None
    if with_view:
        view = ViewConfig(select=[SelectConfig(column="test_source.id")])

    return SourceConfig(
        name="test_source",
        url="http://example.com/data.csv",
        file="data.csv",
        kind=SourceKind.TABULAR,
        separator=",",
        attributes=AttributesConfig(
            original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
        ),
        view=view,
    )


@pytest.mark.unit
class TestViewStageInit:
    """Test ViewStage initialization."""

    def test_initializes_view_builder(self):
        stage = ViewStage()
        assert stage.view_builder is not None
        assert hasattr(stage.view_builder, "build_create_view")

    def test_sets_name_and_description(self):
        stage = ViewStage()
        assert stage.name == "View"
        assert stage.description == "Create database views"


@pytest.mark.unit
class TestViewStageExecute:
    """Test ViewStage.execute() method."""

    def test_creates_view_and_sets_context(self):
        """Test that a view is created and its name stored in context."""
        # Arrange
        stage = ViewStage()
        source = _build_source(with_view=True)

        mock_connection = Mock()
        executed = []
        mock_connection.execute = lambda stmt: executed.append(str(stmt))
        mock_connection.commit = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)

        context = {}

        # Act
        with patch(
            "geoparser.gazetteer.installer.stages.view.get_connection",
            return_value=mock_connection,
        ):
            stage.execute(source, context)

        # Assert
        assert context["view_name"] == "test_source_view"
        assert any("DROP VIEW IF EXISTS test_source_view" in c for c in executed)
        assert any("CREATE VIEW test_source_view" in c for c in executed)

    def test_sets_none_view_name_when_no_view(self):
        """Test that view_name is None when source has no view."""
        # Arrange
        stage = ViewStage()
        source = _build_source(with_view=False)
        context = {}

        # Act
        stage.execute(source, context)

        # Assert
        assert context["view_name"] is None
