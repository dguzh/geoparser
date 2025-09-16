import uuid
from unittest.mock import MagicMock, patch

import pytest

from geoparser.geoparserv2.geoparserv2 import GeoparserV2
from geoparser.modules.recognizers.base import Recognizer
from geoparser.modules.resolvers.base import Resolver


def test_geoparserv2_initialization():
    """Test basic initialization of GeoparserV2."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    assert geoparser.recognizer == mock_recognizer
    assert geoparser.resolver == mock_resolver


def test_parse_single_text():
    """Test parsing a single text string."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    text = "This is a test document about London."

    # Mock the Project methods
    with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Mock return values
        mock_documents = [MagicMock(), MagicMock()]
        mock_project.get_documents.side_effect = [
            mock_documents,  # First call returns all documents
            mock_documents,  # Second call returns filtered documents
        ]

        # Call parse
        result = geoparser.parse(text)

        # Verify Project was created
        mock_project_class.assert_called_once()

        # Verify documents were added
        mock_project.add_documents.assert_called_once_with(text)

        # Verify modules were run
        mock_recognizer.run.assert_called_once_with(mock_documents)
        mock_resolver.run.assert_called_once_with(mock_documents)

        # Verify project was deleted (default behavior)
        mock_project.delete.assert_called_once()

        # Verify result
        assert result == mock_documents


def test_parse_multiple_texts():
    """Test parsing a list of text strings."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    texts = [
        "This is the first document about London.",
        "This is the second document about Paris.",
    ]

    # Mock the Project methods
    with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Mock return values
        mock_documents = [MagicMock(), MagicMock()]
        mock_project.get_documents.side_effect = [
            mock_documents,  # First call returns all documents
            mock_documents,  # Second call returns filtered documents
        ]

        # Call parse
        result = geoparser.parse(texts)

        # Verify documents were added
        mock_project.add_documents.assert_called_once_with(texts)

        # Verify modules were run
        mock_recognizer.run.assert_called_once_with(mock_documents)
        mock_resolver.run.assert_called_once_with(mock_documents)

        # Verify result
        assert result == mock_documents


def test_parse_with_save():
    """Test parsing with save=True preserves the project."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    text = "This is a test document about London."

    # Mock the Project methods
    with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Mock return values
        mock_documents = [MagicMock()]
        mock_project.get_documents.side_effect = [
            mock_documents,  # First call returns all documents
            mock_documents,  # Second call returns filtered documents
        ]

        # Mock print function
        with patch("builtins.print") as mock_print:
            # Call parse with save=True
            result = geoparser.parse(text, save=True)

            # Verify project was NOT deleted
            mock_project.delete.assert_not_called()

            # Verify print was called to inform user
            mock_print.assert_called_once()
            print_call_args = mock_print.call_args[0][0]
            assert "Results saved under project name:" in print_call_args


def test_parse_empty_text():
    """Test parsing empty text."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    # Mock the Project methods
    with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Mock return values
        mock_project.get_documents.side_effect = [
            [],  # First call returns no documents
            [],  # Second call returns no filtered documents
        ]

        # Call parse
        result = geoparser.parse("")

        # Verify project was still created and cleaned up
        mock_project_class.assert_called_once()
        mock_project.delete.assert_called_once()

        # Verify result is empty
        assert result == []


def test_parse_project_cleanup_on_exception():
    """Test that project is cleaned up even when an exception occurs."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    # Mock the Project methods to raise an exception
    with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Make recognizer.run raise an exception
        mock_recognizer.run.side_effect = Exception("Test exception")
        mock_project.get_documents.return_value = [MagicMock()]

        # Call parse and expect exception
        with pytest.raises(Exception, match="Test exception"):
            geoparser.parse("Test text")

        # Verify project was still cleaned up
        mock_project.delete.assert_called_once()


def test_parse_project_name_generation():
    """Test that project names are generated correctly."""
    mock_recognizer = MagicMock(spec=Recognizer)
    mock_resolver = MagicMock(spec=Resolver)

    # Mock the recognizer and resolver IDs
    mock_recognizer.id = uuid.uuid4()
    mock_resolver.id = uuid.uuid4()

    geoparser = GeoparserV2(recognizer=mock_recognizer, resolver=mock_resolver)

    # Mock uuid.uuid4().hex to return a predictable value
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.return_value.hex = "abcdef123456789"

        with patch("geoparser.geoparserv2.geoparserv2.Project") as mock_project_class:
            mock_project = MagicMock()
            mock_project_class.return_value = mock_project
            mock_project.get_documents.return_value = []

            # Call parse
            geoparser.parse("Test text")

            # Verify project was created with first 8 characters of hex
            mock_project_class.assert_called_once_with("abcdef12")
