"""
Unit tests for geoparser/db/models/validators.py

Tests the validator functions.
"""

import pytest


@pytest.mark.unit
class TestNormalizeNewlines:
    """Test the normalize_newlines function."""

    def test_normalizes_windows_newlines(self):
        """Test that Windows-style newlines (\\r\\n) are normalized to \\n."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Line1\r\nLine2\r\nLine3"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Line1\nLine2\nLine3"

    def test_normalizes_mac_newlines(self):
        """Test that Mac-style newlines (\\r) are normalized to \\n."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Line1\rLine2\rLine3"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Line1\nLine2\nLine3"

    def test_preserves_unix_newlines(self):
        """Test that Unix-style newlines (\\n) are preserved."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Line1\nLine2\nLine3"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Line1\nLine2\nLine3"

    def test_handles_mixed_newlines(self):
        """Test that mixed newline styles are all normalized."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Line1\r\nLine2\rLine3\nLine4"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Line1\nLine2\nLine3\nLine4"

    def test_handles_empty_string(self):
        """Test that empty string is handled correctly."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = ""

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == ""

    def test_handles_string_without_newlines(self):
        """Test that strings without newlines are preserved."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Single line text"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Single line text"

    def test_handles_multiple_consecutive_newlines(self):
        """Test that multiple consecutive newlines are normalized correctly."""
        # Arrange
        from geoparser.db.models.validators import normalize_newlines

        text = "Line1\r\n\r\nLine2\r\r\nLine3"

        # Act
        normalized = normalize_newlines(text)

        # Assert
        assert normalized == "Line1\n\nLine2\n\nLine3"
