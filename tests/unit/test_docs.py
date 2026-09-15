"""
Unit tests for the documentation sources.

The transformer spaCy pipeline needs a plugin that neither spaCy nor Geoparser pulls in
on its own, and the plugin's current major line is built for a later spaCy than the one
Geoparser uses. Every public example that reaches for the model therefore has to carry
the same prerequisite, with the same version bound. These tests find those examples
themselves — across every tracked file, whatever its format — so an example added later
cannot quietly go unqualified.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
GUARD = Path(__file__).resolve()

TRANSFORMER_MODEL = "en_core_web_trf"
ALTERNATIVE_MODEL = "en_core_web_lg"
UNSUPPORTED_PYTHON = "3.14"

# The bound `en_core_web_trf` 3.8.0 itself declares. Unpinned, pip installs the 2.x line,
# which targets spaCy 4 and a thinc release spaCy 3.8 cannot use.
PLUGIN_REQUIREMENT = "spacy-curated-transformers>=0.2.2,<1.0.0"

# An install command that names the plugin without immediately constraining it.
UNPINNED_INSTALL = re.compile(
    r"""install\s+["']?spacy-curated-transformers(?![><=~!])"""
)

# The single place the caveat is written, and the line every page pulls it in with.
CAVEAT_SNIPPET = DOCS_DIR / "_snippets" / "spacy-transformer-requirements.rst"
CAVEAT_INCLUDE = ".. include:: /_snippets/spacy-transformer-requirements.rst"


def _tracked_files() -> list[Path]:
    """Every file git tracks, which is every source and no generated artifact."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:  # pragma: no cover
        pytest.skip(f"not a git checkout, cannot enumerate sources: {error}")
    return [REPO_ROOT / name for name in listing.split("\0") if name]


def _read(path: Path) -> str:
    """Read a source as text, or return an empty string if it is not text at all."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _sources_mentioning_transformer_model() -> list[Path]:
    """Every tracked source that presents the transformer model, this guard aside."""
    return sorted(
        path
        for path in _tracked_files()
        if path.resolve() != GUARD and TRANSFORMER_MODEL in _read(path)
    )


def _names(paths: list[Path]) -> list[str]:
    """Repository-relative names, for assertion messages that point somewhere."""
    return [path.relative_to(REPO_ROOT).as_posix() for path in paths]


@pytest.mark.unit
class TestTransformerModelCaveat:
    """Test that transformer examples state what the model needs to run."""

    def test_discovery_finds_sources_but_not_this_guard(self):
        """Test that the scan below is looking at something, and not at itself."""
        # Arrange & Act
        sources = _sources_mentioning_transformer_model()

        # Assert
        assert sources, f"nothing mentions {TRANSFORMER_MODEL}; has the scan narrowed?"
        assert GUARD not in sources
        assert CAVEAT_SNIPPET in sources

    def test_shared_caveat_pins_plugin_and_offers_an_alternative(self):
        """Test that the one copy of the caveat carries all of the facts."""
        # Arrange & Act
        caveat = _read(CAVEAT_SNIPPET)

        # Assert
        assert PLUGIN_REQUIREMENT in caveat
        assert UNSUPPORTED_PYTHON in caveat
        assert ALTERNATIVE_MODEL in caveat

    def test_rst_sources_include_the_shared_caveat(self):
        """Test that no documentation page shows the model without the caveat."""
        # Arrange
        pages = [
            path
            for path in _sources_mentioning_transformer_model()
            if path.suffix == ".rst" and path != CAVEAT_SNIPPET
        ]

        # Act
        unqualified = _names([p for p in pages if CAVEAT_INCLUDE not in _read(p)])

        # Assert
        assert pages, "no documentation page presents the model any more"
        assert not unqualified, (
            f"these pages present {TRANSFORMER_MODEL} without the shared caveat; "
            f"add '{CAVEAT_INCLUDE}' to each: {unqualified}"
        )

    def test_other_sources_state_the_pinned_plugin_requirement(self):
        """Test that sources which cannot use the include state the bound inline."""
        # Arrange
        others = [
            path
            for path in _sources_mentioning_transformer_model()
            if path.suffix != ".rst"
        ]

        # Act
        unqualified = _names([p for p in others if PLUGIN_REQUIREMENT not in _read(p)])

        # Assert
        assert others, "no notebook or build file presents the model any more"
        assert not unqualified, (
            f"these sources present {TRANSFORMER_MODEL} without stating "
            f"'{PLUGIN_REQUIREMENT}': {unqualified}"
        )

    def test_no_source_recommends_installing_the_plugin_unpinned(self):
        """Test that no example installs the plugin without its version bound."""
        # Arrange & Act
        unpinned = _names(
            [
                path
                for path in _tracked_files()
                if path.resolve() != GUARD and UNPINNED_INSTALL.search(_read(path))
            ]
        )

        # Assert
        assert not unpinned, (
            "these sources install spacy-curated-transformers without a version bound, "
            f"which resolves to the 2.x line spaCy 3.8 cannot use: {unpinned}"
        )
