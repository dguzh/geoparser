"""
A guard that public metadata and links point at the canonical repository.

The project is developed through forks, and a fork's clone URL is what every
tool offers you when you copy a link out of a browser. Those URLs work, so a
stale one survives review: the docs build, the page renders, and the "Edit this
page" button quietly sends readers to a fork that may be behind, private, or
gone.

This test pins the three places a fork slug reaches the public -- the MkDocs
repository metadata, the citation record, and every ``github.com`` link to this
repository in tracked files -- and fails when one of them names anything but
the canonical repository.

Only links to *this* repository are checked. Links to other projects, and the
``dguzh/geo-*`` model identifiers on Hugging Face, are unrelated names that
happen to share an owner.
"""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_SLUG = "dguzh/geoparser"
CANONICAL_URL = f"https://github.com/{CANONICAL_SLUG}"

# ``github.com`` followed by an owner and this repository's name, however the
# link continues afterwards -- a blob path, an issue tracker, a bare clone URL.
REPO_LINK = re.compile(r"github\.com/(?P<owner>[A-Za-z0-9][A-Za-z0-9._-]*)/geoparser\b")


def _tracked_text_files() -> list[Path]:
    """Every tracked file that reads back as text, newest checkout state."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    files = []
    for name in listing.stdout.split("\0"):
        if not name:
            continue
        path = ROOT / name
        try:
            path.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # a binary asset, or a path this checkout does not hold
        files.append(path)
    return files


def _repo_links() -> list[tuple[Path, int, str]]:
    """Every link to this repository, as ``(path, line number, owner)``."""
    found = []
    for path in _tracked_text_files():
        for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            for match in REPO_LINK.finditer(line):
                found.append((path, number, match.group("owner")))
    return found


@pytest.mark.unit
class TestCanonicalRepository:
    """The repository this project presents itself as."""

    def test_the_tree_links_to_itself_at_all(self):
        """A sanity check: this guard is not passing because it found nothing."""
        # Act & Assert
        assert _repo_links(), "expected some links to this repository to check"

    def test_every_repository_link_names_the_canonical_owner(self):
        """No tracked file points a reader at a fork."""
        # Act
        stale = [
            f"{path.relative_to(ROOT)}:{number} -> {owner}/geoparser"
            for path, number, owner in _repo_links()
            if owner != CANONICAL_SLUG.split("/")[0]
        ]

        # Assert
        assert not stale, "links to a non-canonical repository:\n" + "\n".join(stale)

    def test_mkdocs_names_the_canonical_repository(self):
        """The docs header and its edit links resolve against the canonical repo."""
        # Arrange
        config = yaml.safe_load((ROOT / "mkdocs.yml").read_text("utf-8"))

        # Act & Assert
        assert config["repo_url"] == CANONICAL_URL
        assert config["repo_name"] == CANONICAL_SLUG

    def test_the_citation_record_names_the_canonical_repository(self):
        """``repository-code`` is what a citation manager resolves to."""
        # Arrange
        citation = yaml.safe_load((ROOT / "CITATION.cff").read_text("utf-8"))

        # Act & Assert
        assert citation["repository-code"] == CANONICAL_URL
