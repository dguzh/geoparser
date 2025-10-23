"""
Unit tests for geoparser/gazetteer/installer/stages/base.py

Tests the Stage abstract base class.
"""

import pytest

from geoparser.gazetteer.installer.model import (
    AttributesConfig,
    DataType,
    OriginalAttributeConfig,
    SourceConfig,
    SourceType,
)
from geoparser.gazetteer.installer.stages.base import Stage


class ConcreteStage(Stage):
    """Concrete implementation of Stage for testing."""

    def __init__(self):
        super().__init__(name="Test Stage", description="A test stage")
        self.executed = False
        self.source_received = None
        self.context_received = None

    def execute(self, source, context):
        """Execute the stage."""
        self.executed = True
        self.source_received = source
        self.context_received = context


@pytest.mark.unit
class TestStageInit:
    """Test Stage initialization."""

    def test_creates_stage_with_name_and_description(self):
        """Test creating a stage with name and description."""
        # Act
        stage = ConcreteStage()

        # Assert
        assert stage.name == "Test Stage"
        assert stage.description == "A test stage"

    def test_cannot_instantiate_abstract_stage(self):
        """Test that abstract Stage cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError):
            Stage(name="Test", description="Test")


@pytest.mark.unit
class TestStageExecute:
    """Test Stage.execute() method."""

    def test_execute_receives_source_and_context(self):
        """Test that execute method receives source and context."""
        # Arrange
        stage = ConcreteStage()
        source = SourceConfig(
            name="test_source",
            url="http://example.com/data.csv",
            file="data.csv",
            type=SourceType.TABULAR,
            separator=",",
            attributes=AttributesConfig(
                original=[OriginalAttributeConfig(name="id", type=DataType.INTEGER)]
            ),
        )
        context = {"key": "value"}

        # Act
        stage.execute(source, context)

        # Assert
        assert stage.executed is True
        assert stage.source_received == source
        assert stage.context_received == context


@pytest.mark.unit
class TestStageStringRepresentation:
    """Test Stage string representations."""

    def test_str_returns_name_and_description(self):
        """Test that __str__ returns name and description."""
        # Arrange
        stage = ConcreteStage()

        # Act
        result = str(stage)

        # Assert
        assert result == "Test Stage: A test stage"

    def test_repr_returns_class_and_name(self):
        """Test that __repr__ returns class name and stage name."""
        # Arrange
        stage = ConcreteStage()

        # Act
        result = repr(stage)

        # Assert
        assert result == "ConcreteStage(name='Test Stage')"
