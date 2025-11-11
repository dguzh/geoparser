"""
Unit tests for geoparser/geoparser/geoparser.py

Tests the Geoparser class with mocked dependencies.
"""

from unittest.mock import Mock, patch

import pytest

from geoparser.geoparser.geoparser import Geoparser


@pytest.mark.unit
class TestGeoparserInitialization:
    """Test Geoparser initialization."""

    def test_creates_with_recognizer_and_resolver(self):
        """Test that Geoparser can be created with recognizer and resolver."""
        # Arrange
        mock_recognizer = Mock()
        mock_resolver = Mock()

        # Act
        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Assert
        assert geoparser.recognizer == mock_recognizer
        assert geoparser.resolver == mock_resolver

    @patch("geoparser.modules.SpacyRecognizer")
    @patch("geoparser.modules.SentenceTransformerResolver")
    def test_creates_default_modules_when_none_provided(
        self, mock_resolver_class, mock_recognizer_class
    ):
        """Test that Geoparser creates default modules when none are provided."""
        # Arrange
        mock_recognizer_instance = Mock()
        mock_resolver_instance = Mock()
        mock_recognizer_class.return_value = mock_recognizer_instance
        mock_resolver_class.return_value = mock_resolver_instance

        # Act
        geoparser = Geoparser()

        # Assert
        mock_recognizer_class.assert_called_once_with()
        mock_resolver_class.assert_called_once_with()
        assert geoparser.recognizer == mock_recognizer_instance
        assert geoparser.resolver == mock_resolver_instance

    def test_accepts_none_for_recognizer(self):
        """Test that Geoparser accepts None for recognizer to skip recognition."""
        # Arrange
        mock_resolver = Mock()

        # Act
        geoparser = Geoparser(recognizer=None, resolver=mock_resolver)

        # Assert
        assert geoparser.recognizer is None
        assert geoparser.resolver == mock_resolver

    def test_accepts_none_for_resolver(self):
        """Test that Geoparser accepts None for resolver to skip resolution."""
        # Arrange
        mock_recognizer = Mock()

        # Act
        geoparser = Geoparser(recognizer=mock_recognizer, resolver=None)

        # Assert
        assert geoparser.recognizer == mock_recognizer
        assert geoparser.resolver is None

    @patch("geoparser.modules.SpacyRecognizer")
    def test_legacy_spacy_model_parameter_shows_deprecation_warning(
        self, mock_recognizer_class
    ):
        """Test that using spacy_model parameter shows deprecation warning."""
        # Arrange
        mock_recognizer_instance = Mock()
        mock_recognizer_class.return_value = mock_recognizer_instance
        mock_resolver = Mock()

        # Act & Assert
        with pytest.warns(DeprecationWarning, match="Deprecated parameter detected"):
            geoparser = Geoparser(resolver=mock_resolver, spacy_model="en_core_web_sm")

        # Should still create recognizer with the model
        mock_recognizer_class.assert_called_once_with(model_name="en_core_web_sm")
        assert geoparser.recognizer == mock_recognizer_instance

    @patch("geoparser.modules.SentenceTransformerResolver")
    def test_legacy_transformer_model_parameter_shows_deprecation_warning(
        self, mock_resolver_class
    ):
        """Test that using transformer_model parameter shows deprecation warning."""
        # Arrange
        mock_resolver_instance = Mock()
        mock_resolver_class.return_value = mock_resolver_instance
        mock_recognizer = Mock()

        # Act & Assert
        with pytest.warns(DeprecationWarning, match="Deprecated parameter detected"):
            geoparser = Geoparser(
                recognizer=mock_recognizer,
                transformer_model="dguzh/geo-all-MiniLM-L6-v2",
            )

        # Should still create resolver with the model
        mock_resolver_class.assert_called_once_with(
            model_name="dguzh/geo-all-MiniLM-L6-v2"
        )
        assert geoparser.resolver == mock_resolver_instance

    @patch("geoparser.modules.SpacyRecognizer")
    @patch("geoparser.modules.SentenceTransformerResolver")
    def test_legacy_parameters_show_single_consolidated_warning(
        self, mock_resolver_class, mock_recognizer_class
    ):
        """Test that using both legacy parameters shows single consolidated warning."""
        # Arrange
        mock_recognizer_instance = Mock()
        mock_resolver_instance = Mock()
        mock_recognizer_class.return_value = mock_recognizer_instance
        mock_resolver_class.return_value = mock_resolver_instance

        # Act & Assert
        with pytest.warns(DeprecationWarning, match="Deprecated parameters detected"):
            geoparser = Geoparser(
                spacy_model="en_core_web_sm",
                transformer_model="dguzh/geo-all-MiniLM-L6-v2",
            )

        # Should create both with the specified models
        mock_recognizer_class.assert_called_once_with(model_name="en_core_web_sm")
        mock_resolver_class.assert_called_once_with(
            model_name="dguzh/geo-all-MiniLM-L6-v2"
        )
        assert geoparser.recognizer == mock_recognizer_instance
        assert geoparser.resolver == mock_resolver_instance


@pytest.mark.unit
class TestGeoparserParse:
    """Test Geoparser parse method."""

    @patch("geoparser.geoparser.geoparser.Project")
    def test_creates_temporary_project_with_uuid_name(self, mock_project_class):
        """Test that parse creates a temporary project with UUID name."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text")

        # Assert
        mock_project_class.assert_called_once()
        # Project name should be 8-character hex
        project_name = mock_project_class.call_args[0][0]
        assert len(project_name) == 8
        assert all(c in "0123456789abcdef" for c in project_name)

    @patch("geoparser.geoparser.geoparser.Project")
    def test_creates_documents_in_project(self, mock_project_class):
        """Test that parse creates documents in the project."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text")

        # Assert
        mock_project_instance.create_documents.assert_called_once_with("Test text")

    @patch("geoparser.geoparser.geoparser.Project")
    def test_runs_recognizer_on_documents(self, mock_project_class):
        """Test that parse runs recognizer on documents."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text")

        # Assert
        mock_project_instance.run_recognizer.assert_called_once_with(mock_recognizer)

    @patch("geoparser.geoparser.geoparser.Project")
    def test_runs_resolver_on_documents(self, mock_project_class):
        """Test that parse runs resolver on documents."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text")

        # Assert
        mock_project_instance.run_resolver.assert_called_once_with(mock_resolver)

    @patch("geoparser.geoparser.geoparser.Project")
    def test_retrieves_documents_with_default_tag(self, mock_project_class):
        """Test that parse retrieves documents using the default 'latest' tag."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec_id"
        mock_resolver = Mock()
        mock_resolver.id = "test_res_id"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text")

        # Assert
        # get_documents is called with default tag parameter
        mock_project_instance.get_documents.assert_called_once_with()

    @patch("geoparser.geoparser.geoparser.Project")
    def test_deletes_project_after_parsing_by_default(self, mock_project_class):
        """Test that parse deletes the project by default (save=False)."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text", save=False)

        # Assert
        mock_project_instance.delete.assert_called_once()

    @patch("geoparser.geoparser.geoparser.Project")
    def test_keeps_project_when_save_is_true(self, mock_project_class):
        """Test that parse doesn't delete the project when save=True."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text", save=True)

        # Assert
        mock_project_instance.delete.assert_not_called()

    @patch("geoparser.geoparser.geoparser.Project")
    def test_returns_processed_documents(self, mock_project_class):
        """Test that parse returns the processed documents."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_doc1 = Mock()
        mock_doc2 = Mock()
        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = [mock_doc1, mock_doc2]
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        result = geoparser.parse("Test text")

        # Assert
        assert len(result) == 2
        assert result[0] == mock_doc1
        assert result[1] == mock_doc2

    @patch("geoparser.geoparser.geoparser.Project")
    def test_handles_list_of_texts(self, mock_project_class):
        """Test that parse handles a list of texts."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse(["Text 1", "Text 2"])

        # Assert
        mock_project_instance.create_documents.assert_called_once_with(
            ["Text 1", "Text 2"]
        )

    @patch("geoparser.geoparser.geoparser.Project")
    @patch("builtins.print")
    def test_prints_project_name_when_saved(self, mock_print, mock_project_class):
        """Test that parse prints the project name when save=True."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.get_documents.return_value = []
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act
        geoparser.parse("Test text", save=True)

        # Assert
        mock_print.assert_called_once()
        print_message = mock_print.call_args[0][0]
        assert "Results saved under project name:" in print_message

    @patch("geoparser.geoparser.geoparser.Project")
    def test_deletes_project_even_if_error_occurs(self, mock_project_class):
        """Test that parse deletes the project even if an error occurs during processing."""
        # Arrange
        mock_recognizer = Mock()
        mock_recognizer.id = "test_rec"
        mock_resolver = Mock()
        mock_resolver.id = "test_res"

        mock_project_instance = Mock()
        mock_project_instance.run_recognizer.side_effect = Exception("Test error")
        mock_project_class.return_value = mock_project_instance

        geoparser = Geoparser(mock_recognizer, mock_resolver)

        # Act & Assert
        with pytest.raises(Exception, match="Test error"):
            geoparser.parse("Test text", save=False)

        # Project should still be deleted in finally block
        mock_project_instance.delete.assert_called_once()
