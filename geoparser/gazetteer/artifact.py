"""
Gazetteer artifact: the canonical, self-contained SQLite file per gazetteer.

An artifact is produced by the build pipeline and is immutable afterwards. It
has a fixed schema shared by every gazetteer:

- ``metadata``: key/value pairs (schema version, gazetteer name, CRS, ...)
- ``feature``: one row per feature (identifier, type, JSON attributes, WKB geometry)
- ``name``: searchable names, one row per (feature, name)
- ``name_fts``: FTS5 index over names (external content on ``name``)
- ``name_soundex``: phonetic codes for fuzzy candidate retrieval

This module owns the artifact schema (used by the build pipeline) and the
read-only runtime access layer (used by the Gazetteer class).
"""

from __future__ import annotations

import os
import sqlite3
import threading
import typing as t
from pathlib import Path

from appdirs import user_data_dir

from geoparser.db.functions import levenshtein, soundex
from geoparser.gazetteer.feature import Feature

# Bump when the artifact schema changes; artifacts with a different version
# must be rebuilt.
SCHEMA_VERSION = "1"

ARTIFACT_SUFFIX = ".db"

FTS_TOKENIZER = "unicode61 remove_diacritics 2 tokenchars '.'"

# Base tables created before data is emitted. Search structures (FTS, soundex,
# indexes) are created afterwards, once all rows are in place.
BASE_SCHEMA = [
    """
    CREATE TABLE metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """,
    """
    CREATE TABLE feature (
        id INTEGER PRIMARY KEY,
        identifier TEXT NOT NULL,
        type TEXT NOT NULL,
        attributes TEXT NOT NULL,
        geometry BLOB
    )
    """,
    """
    CREATE TABLE name (
        id INTEGER PRIMARY KEY,
        feature_id INTEGER NOT NULL REFERENCES feature(id),
        text TEXT NOT NULL
    )
    """,
]

SEARCH_SCHEMA = [
    "CREATE UNIQUE INDEX idx_feature_identifier ON feature(identifier)",
    "CREATE INDEX idx_name_feature_id ON name(feature_id)",
    f"""
    CREATE VIRTUAL TABLE name_fts USING fts5(
        text,
        content='name',
        content_rowid='id',
        tokenize="{FTS_TOKENIZER}"
    )
    """,
    "INSERT INTO name_fts(rowid, text) SELECT id, text FROM name",
    """
    CREATE TABLE name_soundex (
        id INTEGER PRIMARY KEY,
        code TEXT
    )
    """,
    "INSERT INTO name_soundex(id, code) SELECT id, soundex(text) FROM name",
    "CREATE INDEX idx_name_soundex_code ON name_soundex(code)",
]


def gazetteers_dir() -> Path:
    """
    Return the directory holding installed gazetteer artifacts.

    Defaults to the user data directory; can be overridden with the
    ``GEOPARSER_GAZETTEERS_DIR`` environment variable.

    Returns:
        Path to the gazetteers directory
    """
    override = os.getenv("GEOPARSER_GAZETTEERS_DIR")
    if override:
        return Path(override)
    return Path(user_data_dir("geoparser", "")) / "gazetteers"


def artifact_path(gazetteer_name: str) -> Path:
    """
    Return the artifact path for a gazetteer name.

    Args:
        gazetteer_name: Name of the gazetteer

    Returns:
        Path where the gazetteer's artifact is (or will be) installed
    """
    return gazetteers_dir() / f"{gazetteer_name}{ARTIFACT_SUFFIX}"


def list_artifacts() -> t.List[str]:
    """
    List the names of installed gazetteers.

    Returns:
        Sorted list of gazetteer names with an installed artifact
    """
    directory = gazetteers_dir()
    if not directory.exists():
        return []
    return sorted(
        path.stem for path in directory.glob(f"*{ARTIFACT_SUFFIX}") if path.is_file()
    )


def register_functions(connection: sqlite3.Connection) -> None:
    """
    Register the fuzzy matching functions on a SQLite connection.

    Args:
        connection: SQLite connection to register functions on
    """
    connection.create_function("soundex", 1, soundex, deterministic=True)
    connection.create_function("levenshtein", 2, levenshtein, deterministic=True)


class GazetteerArtifact:
    """
    Read-only access to an installed gazetteer artifact.

    Connections are opened read-only and per thread; the artifact file is
    never modified after the build.
    """

    _FEATURE_COLUMNS = "f.id, f.identifier, f.type, f.attributes, f.geometry"

    def __init__(self, path: t.Union[str, Path]):
        """
        Open a gazetteer artifact.

        Args:
            path: Path to the artifact file

        Raises:
            FileNotFoundError: If the artifact file does not exist
            RuntimeError: If the artifact has an incompatible schema version
        """
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Gazetteer artifact not found: {self.path}")
        self._local = threading.local()
        self.metadata = self._read_metadata()
        version = self.metadata.get("schema_version")
        if version != SCHEMA_VERSION:
            raise RuntimeError(
                f"Gazetteer artifact {self.path} has schema version {version!r}, "
                f"but this version of geoparser requires {SCHEMA_VERSION!r}. "
                "Please reinstall the gazetteer."
            )

    @property
    def name(self) -> str:
        """Name of the gazetteer stored in this artifact."""
        return self.metadata["name"]

    @property
    def crs(self) -> str:
        """Coordinate reference system of the artifact's geometries."""
        return self.metadata["crs"]

    def _connection(self) -> sqlite3.Connection:
        """Return the read-only SQLite connection for the current thread."""
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True, check_same_thread=False
            )
            register_functions(connection)
            self._local.connection = connection
        return connection

    def _read_metadata(self) -> t.Dict[str, str]:
        try:
            rows = (
                self._connection().execute("SELECT key, value FROM metadata").fetchall()
            )
        except sqlite3.DatabaseError as error:
            raise RuntimeError(
                f"File {self.path} is not a valid gazetteer artifact: {error}"
            ) from error
        return dict(rows)

    def _features_from_rows(self, rows: t.Iterable[t.Tuple]) -> t.List[Feature]:
        return [
            Feature(
                artifact=self,
                id=row[0],
                identifier=row[1],
                type=row[2],
                attributes=row[3],
                geometry=row[4],
            )
            for row in rows
        ]

    def find(self, identifier: str) -> t.Optional[Feature]:
        """
        Find a feature by its identifier.

        Args:
            identifier: The identifier value of the feature to find

        Returns:
            Feature object if found, None otherwise
        """
        row = (
            self._connection()
            .execute(
                f"SELECT {self._FEATURE_COLUMNS} FROM feature f WHERE f.identifier = ?",
                (str(identifier),),
            )
            .fetchone()
        )
        if row is None:
            return None
        return self._features_from_rows([row])[0]

    def get_feature_names(self, feature_id: int) -> t.List[str]:
        """
        Get all names of a feature.

        Args:
            feature_id: Internal feature id

        Returns:
            List of name strings
        """
        rows = (
            self._connection()
            .execute(
                "SELECT text FROM name WHERE feature_id = ? ORDER BY id",
                (feature_id,),
            )
            .fetchall()
        )
        return [row[0] for row in rows]

    def search_exact(self, name: str, limit: int = 10000) -> t.List[Feature]:
        """
        Find features with a name exactly matching the query.

        Uses the FTS index for case- and diacritics-insensitive matching, then
        keeps only names of exactly the query's length so token matches on
        substrings are excluded.

        Args:
            name: Name string to search for
            limit: Maximum number of results to return

        Returns:
            List of matching features
        """
        rows = (
            self._connection()
            .execute(
                f"""
            SELECT {self._FEATURE_COLUMNS}
            FROM name_fts
            JOIN name n ON n.id = name_fts.rowid
            JOIN feature f ON f.id = n.feature_id
            WHERE name_fts MATCH ? AND length(n.text) = ?
            GROUP BY f.id
            LIMIT ?
            """,
                (f'"{name}"', len(name), limit),
            )
            .fetchall()
        )
        return self._features_from_rows(rows)

    def _search_tiered(
        self, matched_sql: str, parameters: t.Tuple, limit: int, tiers: int
    ) -> t.List[Feature]:
        """
        Run a per-name match query and keep the best score tiers per feature.

        The match query must yield ``(feature_id, score)`` rows (lower scores
        are better). It is materialized because SQLite only allows FTS
        auxiliary functions like bm25 in the immediate full-text query.
        """
        rows = (
            self._connection()
            .execute(
                f"""
            WITH matched AS MATERIALIZED ({matched_sql}),
            scored AS (
                SELECT feature_id, min(score) AS score
                FROM matched
                GROUP BY feature_id
                ORDER BY score ASC
                LIMIT ?
            ),
            tiered AS (
                SELECT feature_id, score,
                       dense_rank() OVER (ORDER BY score ASC) AS tier
                FROM scored
            )
            SELECT {self._FEATURE_COLUMNS}
            FROM feature f
            JOIN tiered t ON f.id = t.feature_id
            WHERE t.tier <= ?
            ORDER BY t.score ASC, f.id ASC
            """,
                (*parameters, limit, tiers),
            )
            .fetchall()
        )
        return self._features_from_rows(rows)

    def search_phrase(
        self, name: str, limit: int = 10000, tiers: int = 1
    ) -> t.List[Feature]:
        """
        Find features whose names contain the query as a contiguous phrase.

        Candidates are scored with BM25 (lower is better) and grouped into
        rank tiers; only the best ``tiers`` tiers are returned.

        Args:
            name: Name string to search for
            limit: Maximum number of candidates to score
            tiers: Number of rank tiers to include

        Returns:
            List of matching features, best matches first
        """
        matched_sql = """
            SELECT n.feature_id AS feature_id, bm25(name_fts) AS score
            FROM name_fts
            JOIN name n ON n.id = name_fts.rowid
            WHERE name_fts MATCH ?
        """
        return self._search_tiered(matched_sql, (f'"{name}"',), limit, tiers)

    def search_partial(
        self, name: str, limit: int = 10000, tiers: int = 1
    ) -> t.List[Feature]:
        """
        Find features whose names match some of the query tokens.

        Tokens are combined with OR for loose matching; candidates are scored
        with BM25 and grouped into rank tiers.

        Args:
            name: Name string to search for
            limit: Maximum number of candidates to score
            tiers: Number of rank tiers to include

        Returns:
            List of matching features, best matches first
        """
        query = " OR ".join(
            f'"{token.strip()}"' for token in name.split() if token.strip()
        )
        matched_sql = """
            SELECT n.feature_id AS feature_id, bm25(name_fts) AS score
            FROM name_fts
            JOIN name n ON n.id = name_fts.rowid
            WHERE name_fts MATCH ?
        """
        return self._search_tiered(matched_sql, (query,), limit, tiers)

    def search_fuzzy(
        self, name: str, limit: int = 10000, tiers: int = 1
    ) -> t.List[Feature]:
        """
        Find features with names that sound like the query.

        Uses Soundex codes for candidate retrieval and Levenshtein edit
        distance for ranking; candidates are grouped into distance tiers.

        Args:
            name: Name string to search for
            limit: Maximum number of candidates to score
            tiers: Number of distance tiers to include

        Returns:
            List of matching features, closest matches first
        """
        matched_sql = """
            SELECT n.feature_id AS feature_id, levenshtein(?, n.text) AS score
            FROM name_soundex s
            JOIN name n ON n.id = s.id
            WHERE s.code = soundex(?)
        """
        return self._search_tiered(matched_sql, (name, name), limit, tiers)

    def count_features(self) -> int:
        """Return the number of features in the artifact."""
        return self._connection().execute("SELECT count(*) FROM feature").fetchone()[0]

    def count_names(self) -> int:
        """Return the number of names in the artifact."""
        return self._connection().execute("SELECT count(*) FROM name").fetchone()[0]

    def close(self) -> None:
        """Close the current thread's connection, if any."""
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None
