"""
Emission of the projected features into the SQLite artifact.

Rows are copied from the DuckDB build tables into a temporary SQLite file in
batches; search structures (FTS5, soundex, indexes) and metadata are built
afterwards, then the file is vacuumed and atomically moved into place.
"""

import sqlite3
import typing as t
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from geoparser.gazetteer import artifact
from geoparser.gazetteer.build.progress import advance, item
from geoparser.gazetteer.config import GazetteerConfig

# Number of rows copied per batch from DuckDB to SQLite
BATCH_SIZE = 50000


def create_artifact_db(path: Path) -> sqlite3.Connection:
    """
    Create a fresh artifact database with the base schema.

    The connection is tuned for bulk writes with a bounded memory footprint:
    the artifact is a throwaway temporary file that is only moved into place
    after a fully successful build, so durability is irrelevant, but memory
    use must stay bounded even for very large gazetteers (tens of millions of
    rows). All temporary data spills to disk rather than RAM.

    Args:
        path: Path of the artifact file to create

    Returns:
        SQLite connection to the new database
    """
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA synchronous=OFF")
    # No rollback journal: avoids buffering the whole bulk-load transaction in
    # memory, which would otherwise grow without bound on large builds.
    connection.execute("PRAGMA journal_mode=OFF")
    # Spill temporary data (index sorts, FTS rebuild, VACUUM) to disk, not RAM.
    connection.execute("PRAGMA temp_store=FILE")
    # Cap the page cache so memory stays bounded regardless of data size
    # (negative value = cache size in KiB, here 64 MiB).
    connection.execute("PRAGMA cache_size=-65536")
    for statement in artifact.BASE_SCHEMA:
        connection.execute(statement)
    return connection


def copy_rows(
    duckdb_connection: duckdb.DuckDBPyConnection,
    sqlite_connection: sqlite3.Connection,
    select_sql: str,
    insert_sql: str,
    bar: t.Any,
) -> int:
    """
    Copy rows from a DuckDB query into a SQLite table in batches.

    Args:
        duckdb_connection: DuckDB connection to read from
        sqlite_connection: SQLite connection to write to
        select_sql: DuckDB query producing the rows
        insert_sql: SQLite INSERT statement with positional placeholders
        bar: Item bar to report copy progress on, as a percentage of the
            total row count (known up front from a cheap count query)

    Returns:
        Number of copied rows
    """
    total = duckdb_connection.execute(
        f"SELECT count(*) FROM ({select_sql})"
    ).fetchone()[0]
    cursor = duckdb_connection.execute(select_sql)
    copied = 0
    sqlite_connection.execute("BEGIN")
    while True:
        batch = cursor.fetchmany(BATCH_SIZE)
        if not batch:
            break
        sqlite_connection.executemany(insert_sql, batch)
        copied += len(batch)
        if total:
            bar.set_progress(min(100.0, copied / total * 100))
    sqlite_connection.execute("COMMIT")
    return copied


def emit(
    duckdb_connection: duckdb.DuckDBPyConnection,
    sqlite_connection: sqlite3.Connection,
) -> t.Tuple[int, int]:
    """
    Copy the projected features and names into the artifact.

    Expects the DuckDB build tables ``_features_final`` (id, identifier, source,
    data, geometry) and ``_names_final`` (feature_id, text) to exist.

    Args:
        duckdb_connection: DuckDB connection holding the build tables
        sqlite_connection: SQLite connection of the artifact being built

    Returns:
        Tuple of (feature count, name count)
    """
    with item("Writing features", total=100) as bar:
        feature_count = copy_rows(
            duckdb_connection,
            sqlite_connection,
            "SELECT id, identifier, source, data, geometry "
            "FROM _features_final ORDER BY id",
            "INSERT INTO feature (id, identifier, source, data, geometry) "
            "VALUES (?, ?, ?, ?, ?)",
            bar,
        )
    advance()
    with item("Writing names", total=100) as bar:
        name_count = copy_rows(
            duckdb_connection,
            sqlite_connection,
            "SELECT feature_id, text FROM _names_final ORDER BY feature_id, text",
            "INSERT INTO name (feature_id, text) VALUES (?, ?)",
            bar,
        )
    advance()
    return feature_count, name_count


def finalize(
    sqlite_connection: sqlite3.Connection,
    config: GazetteerConfig,
    feature_count: int,
    name_count: int,
) -> None:
    """
    Build the search structures and metadata, then compact the artifact.

    Args:
        sqlite_connection: SQLite connection of the artifact being built
        config: The gazetteer configuration that was built
        feature_count: Number of emitted features
        name_count: Number of emitted names
    """
    artifact.register_functions(sqlite_connection)

    sqlite_connection.execute("BEGIN")
    with item("Building indexes", total=100) as bar:
        statements = artifact.SEARCH_SCHEMA
        for i, statement in enumerate(statements, start=1):
            sqlite_connection.execute(statement)
            bar.set_progress(i / len(statements) * 100)
    advance()

    metadata = {
        "schema_version": artifact.SCHEMA_VERSION,
        "name": config.name,
        "crs": config.crs,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_count": str(feature_count),
        "name_count": str(name_count),
    }
    with item("Writing metadata", total=100) as bar:
        rows = list(metadata.items())
        for i, row in enumerate(rows, start=1):
            sqlite_connection.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?)", row
            )
            bar.set_progress(i / len(rows) * 100)
        sqlite_connection.execute("COMMIT")
    advance()

    with item("Verifying integrity", total=100) as bar:
        # The emitted counts must match what is actually stored
        stored_features = sqlite_connection.execute(
            "SELECT count(*) FROM feature"
        ).fetchone()[0]
        bar.set_progress(50)
        stored_names = sqlite_connection.execute(
            "SELECT count(*) FROM name"
        ).fetchone()[0]
        bar.set_progress(100)
        if stored_features != feature_count or stored_names != name_count:
            raise RuntimeError(
                f"Artifact integrity check failed: expected {feature_count} features "
                f"and {name_count} names, found {stored_features} and {stored_names}"
            )
    advance()

    with item("Compacting artifact", total=100) as bar:
        sqlite_connection.execute("ANALYZE")
        bar.set_progress(50)
        sqlite_connection.execute("VACUUM")
        bar.set_progress(100)
    advance()
