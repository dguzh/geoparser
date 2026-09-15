"""
Unit tests for the documentation sources.

The transformer spaCy pipeline needs a plugin that neither spaCy nor Geoparser pulls in
on its own, so every public example that reaches for it has to carry the same
prerequisite caveat. These tests keep that true for examples added later.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

TRANSFORMER_MODEL = "en_core_web_trf"
PLUGIN = "spacy-curated-transformers"
ALTERNATIVE_MODEL = "en_core_web_lg"
UNSUPPORTED_PYTHON = "3.14"

# The single place the caveat is written, and the line every page pulls it in with.
CAVEAT_SNIPPET = DOCS_DIR / "_snippets" / "spacy-transformer-requirements.rst"
CAVEAT_INCLUDE = ".. include:: /_snippets/spacy-transformer-requirements.rst"

# Documentation that is not reStructuredText and so cannot use the shared include. It is
# held to naming the plugin instead.
OTHER_DOC_SOURCES = [REPO_ROOT / "demo" / "demo.ipynb"]


def _read(path: Path) -> str:
    """Read a documentation source as text."""
    return path.read_text(encoding="utf-8")


def _rst_pages_mentioning_transformer_model() -> list[Path]:
    """Every documentation page that presents the transformer model, snippet aside."""
    return sorted(
        path
        for path in DOCS_DIR.rglob("*.rst")
        if path != CAVEAT_SNIPPET and TRANSFORMER_MODEL in _read(path)
    )


@pytest.mark.unit
class TestTransformerModelCaveat:
    """Test that transformer examples state what the model needs to run."""

    def test_shared_caveat_names_plugin_python_version_and_alternative(self):
        """Test that the one copy of the caveat carries all three facts."""
        # Arrange & Act
        caveat = _read(CAVEAT_SNIPPET)

        # Assert
        assert PLUGIN in caveat
        assert UNSUPPORTED_PYTHON in caveat
        assert ALTERNATIVE_MODEL in caveat

    def test_rst_pages_with_transformer_model_include_shared_caveat(self):
        """Test that no documentation page shows the model without the caveat."""
        # Arrange
        pages = _rst_pages_mentioning_transformer_model()

        # Act
        unqualified = [
            page.relative_to(REPO_ROOT).as_posix()
            for page in pages
            if CAVEAT_INCLUDE not in _read(page)
        ]

        # Assert
        assert pages, f"no documentation page mentions {TRANSFORMER_MODEL} any more"
        assert not unqualified, (
            f"these pages present {TRANSFORMER_MODEL} without the shared caveat; "
            f"add '{CAVEAT_INCLUDE}' to each: {unqualified}"
        )

    def test_other_doc_sources_with_transformer_model_name_the_plugin(self):
        """Test that non-reStructuredText documentation states the prerequisite too."""
        # Arrange & Act
        unqualified = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in OTHER_DOC_SOURCES
            if TRANSFORMER_MODEL in _read(path) and PLUGIN not in _read(path)
        ]

        # Assert
        assert not unqualified, (
            f"these sources present {TRANSFORMER_MODEL} without naming {PLUGIN}: "
            f"{unqualified}"
        )
