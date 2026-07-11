"""
Gazetteer builder: compiles a declarative config into a SQLite artifact.

The build pipeline has three stages, each its own progress group:

1. Preparing sources: resolve (download/extract, cached across builds) and
   load each source's file into a transient DuckDB table
2. Deriving features: compile and run one projection per feature block,
   producing canonical (identifier, source, data, geometry) and
   (identifier, name) rows, then merge rows that share an identifier
3. Building artifact: copy the derived rows into a temporary SQLite file,
   build its search structures and metadata, then atomically move it into
   place

The staging database and all intermediate tables are discarded after the
build; the artifact is the only output.
"""

import contextlib
import os
import shutil
import typing as t
from pathlib import Path

import duckdb

from geoparser.gazetteer import artifact
from geoparser.gazetteer.build.acquire import Acquirer
from geoparser.gazetteer.build.compile import ProjectionCompiler
from geoparser.gazetteer.build.emit import create_artifact_db, emit, finalize
from geoparser.gazetteer.build.progress import (
    advance,
    build_display,
    item,
    label_suffixes,
    print_build_header,
    print_build_summary,
    stage,
    track,
)
from geoparser.gazetteer.build.stage import Stager, quote_literal
from geoparser.gazetteer.config import FeatureConfig, GazetteerConfig


@contextlib.contextmanager
def _sqlite_tmpdir(directory: Path) -> t.Iterator[None]:
    """
    Temporarily point SQLite's temporary storage at ``directory``.

    SQLite has no per-connection temp-directory setting, so its location is
    controlled through the ``SQLITE_TMPDIR`` environment variable, which is
    read when temporary files are created.

    Args:
        directory: Directory SQLite should use for temporary files
    """
    previous = os.environ.get("SQLITE_TMPDIR")
    os.environ["SQLITE_TMPDIR"] = str(directory)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SQLITE_TMPDIR", None)
        else:
            os.environ["SQLITE_TMPDIR"] = previous


class GazetteerBuilder:
    """
    Builds gazetteer artifacts from declarative configuration files.
    """

    # Fraction of physical memory the staging engine may use before it starts
    # spilling intermediate data to disk.
    _MEMORY_FRACTION = 0.6
    # Headroom always left for the OS, the Python process and the SQLite
    # writer, so the whole build never approaches the machine's memory cap.
    _MEMORY_HEADROOM_MB = 1536
    # Never bound the staging engine below this, or builds become impractically
    # slow.
    _MIN_MEMORY_MB = 512

    def build(
        self, config_path: t.Union[str, Path], keep_downloads: bool = False
    ) -> Path:
        """
        Build and install a gazetteer from a configuration file.

        Args:
            config_path: Path to the YAML configuration file
            keep_downloads: Whether to keep downloaded files after the build

        Returns:
            Path of the installed artifact
        """
        config = GazetteerConfig.from_yaml(config_path)
        print_build_header(config.name)

        target_path = artifact.artifact_path(config.name)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        downloads_dir = target_path.parent / ".downloads" / config.name
        acquirer = Acquirer(downloads_dir)
        build_dir = target_path.parent / f".build-{config.name}"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)

        try:
            with build_display():
                connection = duckdb.connect(str(build_dir / "staging.duckdb"))
                try:
                    self._configure_staging(connection, build_dir)
                    if self._needs_spatial(config):
                        with item("Loading spatial extension", total=100) as bar:
                            self._load_spatial_extension(connection)
                            bar.set_progress(100)
                    self._prepare_sources(acquirer, connection, config)
                    self._derive_features(connection, config)
                    feature_count, name_count = self._build_artifact(
                        connection, config, build_dir, target_path
                    )
                finally:
                    connection.close()
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
            if not keep_downloads:
                acquirer.cleanup()

        print_build_summary(feature_count, name_count)
        return target_path

    def _configure_staging(
        self, connection: duckdb.DuckDBPyConnection, build_dir: Path
    ) -> None:
        """
        Bound the staging engine's memory and make it spill to disk.

        Large gazetteers (GeoNames is ~13M rows) do not fit in memory. By
        default DuckDB sizes its memory limit to a large fraction of RAM and
        only spills relative to that limit, so on memory-constrained machines
        (or WSL, where the reported RAM is the VM's) the process can be killed
        by the OS before it decides to spill. Capping the limit with headroom
        and pointing the temporary directory at on-disk build storage keeps
        peak memory bounded regardless of the machine's specs.

        Args:
            connection: DuckDB connection used for staging and projection
            build_dir: Directory holding the transient build files
        """
        # DuckDB tracks query progress internally only while its progress bar
        # feature is enabled. By default it also prints that progress straight
        # to the terminal, outside Rich's control, which would desync the live
        # build display (stray bars flashing in, stage rows appearing to
        # repeat); ``enable_progress_bar_print`` keeps the tracking without
        # the printing, so `connection.query_progress()` (used to drive our
        # own item bars, see ``Stager`` and ``_derive_features``) works while
        # the terminal stays under our control. ``progress_bar_time = 0``
        # makes tracking start immediately rather than after DuckDB's default
        # delay for what it guesses will be a short query.
        connection.execute("SET enable_progress_bar = true")
        connection.execute("SET enable_progress_bar_print = false")
        connection.execute("SET progress_bar_time = 0")

        temp_dir = build_dir / "duckdb-temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        connection.execute(
            f"SET temp_directory = {quote_literal(str(temp_dir))}"
        )
        # Ordering is established explicitly where it matters (row ids, emit),
        # so let DuckDB avoid buffering results just to preserve input order.
        connection.execute("SET preserve_insertion_order = false")
        memory_limit_mb = self._memory_limit_mb()
        if memory_limit_mb is not None:
            connection.execute(f"SET memory_limit = '{memory_limit_mb}MB'")

    def _memory_limit_mb(self) -> t.Optional[int]:
        """Return a conservative staging memory limit in MiB, or None."""
        total_bytes = self._physical_memory_bytes()
        if total_bytes is None:
            return None
        total_mb = total_bytes / (1024 * 1024)
        limit_mb = min(
            total_mb * self._MEMORY_FRACTION,
            total_mb - self._MEMORY_HEADROOM_MB,
        )
        return int(max(limit_mb, self._MIN_MEMORY_MB))

    @staticmethod
    def _physical_memory_bytes() -> t.Optional[int]:
        """Return the machine's physical memory in bytes, if detectable."""
        try:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        except (ValueError, OSError, AttributeError):
            return None

    def _needs_spatial(self, config: GazetteerConfig) -> bool:
        """Whether the build requires DuckDB's spatial extension."""
        if any(not source_config.is_tabular for source_config in config.sources):
            return True
        return any(feature.geometry is not None for feature in config.features)

    def _load_spatial_extension(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Install and load the DuckDB spatial extension."""
        try:
            connection.install_extension("spatial")
            connection.load_extension("spatial")
        except duckdb.Error as error:
            raise RuntimeError(
                "Failed to load the DuckDB spatial extension, which is required "
                "to build gazetteers with geometries. The extension is downloaded "
                "on first use; make sure you have network access, then try again. "
                f"Original error: {error}"
            ) from error

    def _prepare_sources(
        self,
        acquirer: Acquirer,
        connection: duckdb.DuckDBPyConnection,
        config: GazetteerConfig,
    ) -> None:
        """
        Resolve, then load, each source's data file in turn.

        Acquiring (see :mod:`acquire`) and staging (see :mod:`stage`) each
        report their own items as they run their actual downloads,
        extractions and queries, and advance the stage themselves as each
        one finishes; how many a given source shows depends on whether it
        needed downloading/extracting and whether it is spatial, so the
        estimate below undercounts some sources and overcounts others, but
        the stage's total grows on the fly to stay ahead of it either way.
        """
        stager = Stager(connection)
        total_estimate = sum(
            1 + (1 if source_config.is_tabular else 2)
            for source_config in config.sources
        )
        with stage("Preparing sources", "Prepared sources", total_estimate):
            for source_config in config.sources:
                file_path = acquirer.acquire(source_config)
                stager.stage(source_config, file_path)

    def _derive_features(
        self, connection: duckdb.DuckDBPyConnection, config: GazetteerConfig
    ) -> None:
        """Run each feature block's projection, then merge across blocks."""
        # Every source declares its attributes, so the catalog is derived
        # directly from the config; the staged tables carry exactly this schema.
        catalog = {
            source_config.name: [
                attribute.name for attribute in source_config.attributes
            ]
            for source_config in config.sources
        }
        compiler = ProjectionCompiler(config, catalog)

        connection.execute(
            "CREATE TABLE _features (identifier VARCHAR, source VARCHAR, "
            "data VARCHAR, geometry BLOB)"
        )
        connection.execute("CREATE TABLE _names (identifier VARCHAR, text VARCHAR)")

        # Each feature block shows one item for assembling its features, one
        # per name it collects, and (only if it has a geometry) one for
        # checking whether any identifier repeats; the stage's total grows on
        # the fly to cover the further "merging duplicates" item that shows
        # up only when duplicates are actually found.
        total_estimate = 3
        for feature in config.features:
            total_estimate += 1 + len(compiler.name_queries(feature))
            if compiler.duplicate_geometry_query(feature) is not None:
                total_estimate += 1

        with stage("Deriving features", "Derived features", total_estimate):
            for feature in config.features:
                self._derive_feature(connection, compiler, feature)

            # Merging rows across feature blocks (the checks and joins below)
            # means scanning the whole of _features and _names, which for a
            # large gazetteer is not instantaneous; each gets its own item
            # rather than leaving a silent gap after the last feature block.
            with item("Checking identifiers", total=100) as bar:
                track(
                    bar,
                    connection.query_progress,
                    lambda: self._check_duplicate_identifiers(connection),
                )
            advance()

            # Deterministic internal ids; names of unknown identifiers (e.g.
            # from a related names input covering more places) are dropped by
            # the join below.
            with item("Assigning feature ids", total=100) as bar:
                track(
                    bar,
                    connection.query_progress,
                    lambda: connection.execute(
                        "CREATE TABLE _features_final AS "
                        "SELECT row_number() OVER (ORDER BY identifier) AS id, "
                        "* FROM _features"
                    ),
                )
            advance()

            with item("Linking names", total=100) as bar:
                track(
                    bar,
                    connection.query_progress,
                    lambda: connection.execute(
                        "CREATE TABLE _names_final AS "
                        "SELECT DISTINCT f.id AS feature_id, n.text "
                        "FROM _names n JOIN _features_final f USING (identifier)"
                    ),
                )
            advance()

        total = connection.execute("SELECT count(*) FROM _features_final").fetchone()[0]
        if total == 0:
            raise ValueError(
                "The build produced no features; check the configuration's "
                "'features' blocks and input files"
            )

    def _derive_feature(
        self,
        connection: duckdb.DuckDBPyConnection,
        compiler: ProjectionCompiler,
        feature: FeatureConfig,
    ) -> None:
        """
        Run one feature block's queries, each reported as its own item.

        Each item advances the active stage as soon as it finishes, rather
        than only once every query for this feature block has run.
        """
        with item(f"Assembling features from {feature.source}", total=100) as bar:
            track(
                bar,
                connection.query_progress,
                lambda: connection.execute(
                    f"INSERT INTO _features {compiler.feature_query(feature)}"
                ),
            )
        advance()
        name_queries = compiler.name_queries(feature)
        # A feature block commonly collects several names (a primary name,
        # alternate names, ...), all from the same source, so this loop is
        # the most common source of identical-looking, back-to-back items;
        # number them whenever there is more than one, so a repeat reads as
        # a distinct new item rather than the previous one's bar restarting.
        name_suffixes = label_suffixes(
            [f"Collecting names from {feature.source}"] * len(name_queries)
        )
        for name_query, name_suffix in zip(name_queries, name_suffixes):
            with item(
                f"Collecting names from {feature.source}{name_suffix}", total=100
            ) as bar:
                track(
                    bar,
                    connection.query_progress,
                    lambda nq=name_query: connection.execute(
                        f"INSERT INTO _names {nq}"
                    ),
                )
            advance()
        self._merge_duplicate_geometries(connection, compiler, feature)

    def _merge_duplicate_geometries(
        self,
        connection: duckdb.DuckDBPyConnection,
        compiler: ProjectionCompiler,
        feature: FeatureConfig,
    ) -> None:
        """
        Union the geometries of identifiers that repeat within a source.

        The feature query keeps only the first row's geometry (a bounded
        aggregate); here we recompute the union for the few genuinely
        duplicated identifiers and patch those rows. Doing this only for
        duplicates keeps ``ST_Union_Agg``'s unmanaged memory bounded, so the
        build stays within limits even for very large sources.
        """
        query = compiler.duplicate_geometry_query(feature)
        if query is None:
            return
        with item(f"Checking duplicates in {feature.source}", total=100) as bar:
            track(
                bar,
                connection.query_progress,
                lambda: connection.execute(
                    f"CREATE OR REPLACE TEMP TABLE _dup_geometry AS {query}"
                ),
            )
        advance()
        try:
            has_duplicates = connection.execute(
                "SELECT count(*) FROM _dup_geometry"
            ).fetchone()[0]
            if has_duplicates:
                with item(
                    f"Merging duplicates in {feature.source}", total=100
                ) as bar:
                    track(
                        bar,
                        connection.query_progress,
                        lambda: connection.execute(
                            "UPDATE _features SET geometry = ("
                            "SELECT geometry FROM _dup_geometry d "
                            "WHERE d.identifier = _features.identifier"
                            ") WHERE identifier IN "
                            "(SELECT identifier FROM _dup_geometry)"
                        ),
                    )
                advance()
        finally:
            connection.execute("DROP TABLE IF EXISTS _dup_geometry")

    def _check_duplicate_identifiers(
        self, connection: duckdb.DuckDBPyConnection
    ) -> None:
        """Fail the build when an identifier appears in multiple feature blocks."""
        duplicates = connection.execute(
            "SELECT identifier, string_agg(DISTINCT source, ', ') "
            "FROM _features GROUP BY identifier HAVING count(*) > 1 LIMIT 5"
        ).fetchall()
        if duplicates:
            examples = "; ".join(
                f"'{identifier}' (sources: {sources})"
                for identifier, sources in duplicates
            )
            raise ValueError(
                "Identifiers must be unique across the whole gazetteer, but the "
                f"following appear in multiple feature blocks: {examples}. "
                "Merge the blocks or disambiguate the identifiers with an "
                "expression (e.g. a source prefix)."
            )

    def _build_artifact(
        self,
        connection: duckdb.DuckDBPyConnection,
        config: GazetteerConfig,
        build_dir: Path,
        target_path: Path,
    ) -> t.Tuple[int, int]:
        """Write the artifact file and atomically move it into place."""
        temporary_path = build_dir / target_path.name
        # Keep SQLite's temporary files (FTS rebuild, index sorts, VACUUM) on
        # the build volume rather than the default location, which on some
        # systems (e.g. WSL's /tmp) is a RAM-backed tmpfs and would defeat the
        # point of spilling to disk.
        sqlite_temp_dir = build_dir / "sqlite-temp"
        sqlite_temp_dir.mkdir(parents=True, exist_ok=True)
        with _sqlite_tmpdir(sqlite_temp_dir):
            sqlite_connection = create_artifact_db(temporary_path)
            try:
                with stage("Building artifact", "Built artifact", 6):
                    feature_count, name_count = emit(connection, sqlite_connection)
                    finalize(sqlite_connection, config, feature_count, name_count)
            finally:
                sqlite_connection.close()
        os.replace(temporary_path, target_path)
        return feature_count, name_count


def uninstall(gazetteer_name: str) -> bool:
    """
    Remove an installed gazetteer artifact.

    Args:
        gazetteer_name: Name of the gazetteer to remove

    Returns:
        True if an artifact was removed, False if none was installed
    """
    path = artifact.artifact_path(gazetteer_name)
    if path.exists():
        path.unlink()
        return True
    return False
