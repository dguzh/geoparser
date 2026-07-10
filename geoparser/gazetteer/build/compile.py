"""
Projection compiler: turns feature blocks into DuckDB SQL.

Each feature block compiles into:

- one *feature query* producing ``(identifier, source, data, geometry)`` rows,
  where rows sharing an identifier are merged (names collected, geometries
  unioned, data values taken from the first row)
- one or more *name queries* producing ``(identifier, text)`` rows from the
  block's name specs (own columns or scalar expressions, including expressions
  that expand into several names such as ``unnest(string_split(...))``)

Both kinds of query select from the block's source (aliased ``src``) with the
block's raw SQL joins appended. Column references resolve as follows: a bare
identifier is a column of the block's source (qualified to ``src``); anything
else is a scalar SQL expression or a qualified reference (``<source>.<column>``)
passed through, with its bare identifiers qualified to ``src``. The same rule is
applied inside each join's ``ON`` condition, so join clauses can reference the
block's source columns bare (without a ``src.`` prefix) too.

Geometry of rows sharing an identifier must be unioned, but ``ST_Union_Agg``
holds unmanaged (unspillable) memory proportional to the number of groups, which
is prohibitive for large sources of mostly-unique identifiers. The feature query
therefore keeps the *first* row's geometry (a bounded aggregate), and geometries
are unioned only for the few genuinely duplicated identifiers in a separate,
bounded pass (:meth:`ProjectionCompiler.duplicate_geometry_query`).
"""

import re
import typing as t

from geoparser.gazetteer.build.stage import (
    quote_identifier,
    quote_literal,
)
from geoparser.gazetteer.config import (
    FeatureConfig,
    GazetteerConfig,
)

# Reference to the source row order, used for deterministic "first" merge
# semantics when rows sharing an identifier are collapsed.
ROW_ORDER_REFERENCE = "src.rowid"

_BARE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Matches string literals, quoted identifiers and bare identifiers so
# expressions can be scanned token by token.
_EXPRESSION_TOKEN = re.compile(
    r"'(?:[^']|'')*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_]*"
)


def qualify_expression(expression: str, replacements: t.Mapping[str, str]) -> str:
    """
    Replace bare column references in a scalar SQL expression.

    Used for expressions evaluated over the joined relation, where an
    unqualified column name could be ambiguous between the feature's source and
    a joined source. String literals, quoted identifiers, already-qualified
    references, and function names are left untouched.

    Args:
        expression: Scalar SQL expression
        replacements: Mapping of bare column names to qualified references

    Returns:
        Expression with bare column references replaced
    """

    def replace(match: re.Match) -> str:
        token = match.group(0)
        if token.startswith("'") or token.startswith('"'):
            return token
        if token not in replacements:
            return token
        # Skip already-qualified references (preceded by a dot)
        before = expression[: match.start()].rstrip()
        if before.endswith("."):
            return token
        # Skip function calls (followed by an opening parenthesis)
        after = expression[match.end() :].lstrip()
        if after.startswith("("):
            return token
        return replacements[token]

    return _EXPRESSION_TOKEN.sub(replace, expression)


class CompileError(ValueError):
    """Raised when a feature block cannot be compiled against the staged data."""


class ProjectionCompiler:
    """
    Compiles feature blocks of a gazetteer config into DuckDB SQL.

    The compiler knows the columns of the staged sources (the catalog) to
    resolve and validate bare column references against the block's source.
    """

    def __init__(
        self, config: GazetteerConfig, catalog: t.Dict[str, t.List[str]]
    ):
        """
        Initialize the compiler.

        Args:
            config: Validated gazetteer configuration
            catalog: Mapping of staged source names to their column names
        """
        self.config = config
        self.catalog = catalog
        self._sources = {source.name: source for source in config.sources}

    def feature_query(self, feature: FeatureConfig) -> str:
        """
        Compile the feature query for a feature block.

        The query yields one row per distinct identifier with columns
        ``identifier`` (VARCHAR), ``source`` (VARCHAR), ``data`` (JSON text)
        and ``geometry`` (WKB blob or NULL).

        Args:
            feature: Feature block to compile

        Returns:
            DuckDB SQL string
        """
        from_clause = self._from_clause(feature)
        identifier = self._resolve(feature, feature.identifier, "identifier")

        data_parts = []
        for item in feature.data:
            value = self._resolve(
                feature, item.attribute, f"data value '{item.output_name}'"
            )
            data_parts.append(
                f"{quote_literal(item.output_name)}: {self._first(value)}"
            )
        if data_parts:
            data_sql = f"CAST(to_json({{{', '.join(data_parts)}}}) AS VARCHAR)"
        else:
            data_sql = "'{}'"

        geometry_sql = self._geometry_select(feature)

        return (
            f"SELECT\n"
            f"    CAST(({identifier}) AS VARCHAR) AS identifier,\n"
            f"    {quote_literal(feature.source)} AS source,\n"
            f"    {data_sql} AS data,\n"
            f"    {geometry_sql} AS geometry\n"
            f"{from_clause}\n"
            f"WHERE ({identifier}) IS NOT NULL\n"
            f"GROUP BY 1"
        )

    def name_queries(self, feature: FeatureConfig) -> t.List[str]:
        """
        Compile the name queries for a feature block.

        Each query yields ``(identifier, text)`` rows with trimmed, non-empty
        name strings. A name is a column or scalar expression; an expression
        that produces a list (e.g. ``unnest(string_split(alt, ','))``) expands
        into one name row per element.

        Args:
            feature: Feature block to compile

        Returns:
            List of DuckDB SQL strings
        """
        from_clause = self._from_clause(feature)
        identifier = self._resolve(feature, feature.identifier, "identifier")

        queries = []
        for name in feature.names:
            value = self._resolve(feature, name, "name")
            part = f"CAST(({value}) AS VARCHAR)"
            queries.append(
                f"SELECT DISTINCT identifier, trim(part) AS text\n"
                f"FROM (\n"
                f"    SELECT CAST(({identifier}) AS VARCHAR) AS identifier, "
                f"{part} AS part\n"
                f"    {from_clause}\n"
                f"    WHERE ({identifier}) IS NOT NULL\n"
                f")\n"
                f"WHERE part IS NOT NULL AND trim(part) <> ''"
            )
        return queries

    def duplicate_geometry_query(
        self, feature: FeatureConfig
    ) -> t.Optional[str]:
        """
        Compile the geometry-merge query for duplicated identifiers.

        Returns SQL yielding ``(identifier, geometry)`` rows only for
        identifiers that occur in more than one source row, with their
        geometries unioned into a single WKB blob. Returns ``None`` when the
        block has no geometry.

        This runs over the block's source alone (no joins): a feature's
        geometry depends only on its source, and the block's left joins never
        change a row's geometry, so a joined fan-out cannot affect the union.
        Restricting ``ST_Union_Agg`` to the few duplicated identifiers keeps its
        (unmanaged) memory bounded.

        Args:
            feature: Feature block to compile

        Returns:
            DuckDB SQL string, or None if the block has no geometry
        """
        if feature.geometry is None:
            return None
        identifier = self._resolve(feature, feature.identifier, "identifier")
        geometry = self._feature_geometry(feature)
        source = quote_identifier(feature.source)
        return (
            f"WITH src_rows AS (\n"
            f"    SELECT CAST(({identifier}) AS VARCHAR) AS identifier, "
            f"{geometry} AS geom\n"
            f"    FROM {source} AS src\n"
            f"    WHERE ({identifier}) IS NOT NULL\n"
            f"),\n"
            f"dups AS (\n"
            f"    SELECT identifier FROM src_rows GROUP BY 1 HAVING count(*) > 1\n"
            f")\n"
            f"SELECT r.identifier,\n"
            f"    CASE WHEN count(r.geom) = 0 THEN NULL "
            f"ELSE ST_AsWKB(ST_Union_Agg(r.geom)) END AS geometry\n"
            f"FROM src_rows r SEMI JOIN dups USING (identifier)\n"
            f"GROUP BY 1"
        )

    def _from_clause(self, feature: FeatureConfig) -> str:
        """
        Build the FROM clause for a feature block.

        The block's source is aliased ``src`` and the block's raw SQL join
        clauses are appended, with bare source columns in each join's ``ON``
        condition qualified to ``src`` (so joins need no ``src.`` prefix).
        """
        lines = [f"FROM {quote_identifier(feature.source)} AS src"]
        lines.extend(self._qualify_join(feature, join) for join in feature.joins)
        return "\n".join(lines)

    def _qualify_join(self, feature: FeatureConfig, clause: str) -> str:
        """
        Qualify bare source columns within a join clause's ``ON`` condition.

        Only the condition after the first ``ON`` keyword is rewritten, so the
        joined table and alias are left untouched. Clauses without an ``ON``
        (e.g. ``USING``/``CROSS JOIN``) are returned unchanged.
        """
        match = re.search(r"\sON\s", clause, re.IGNORECASE)
        if match is None:
            return clause
        replacements = {
            column: f'src."{column}"' for column in self.catalog[feature.source]
        }
        cut = match.end()
        return clause[:cut] + qualify_expression(clause[cut:], replacements)

    def _geometry_select(self, feature: FeatureConfig) -> str:
        """
        Build the (bounded) geometry expression for the feature query.

        Keeps the first row's geometry as WKB. Geometries of duplicated
        identifiers are unioned separately (see ``duplicate_geometry_query``).
        """
        if feature.geometry is None:
            return "NULL"
        geometry = self._feature_geometry(feature)
        # ``count`` keeps geometry-less features NULL (arg_min over an all-NULL
        # group would otherwise still be NULL, but this is explicit and matches
        # the union pass).
        return (
            f"CASE WHEN count({geometry}) = 0 THEN NULL "
            f"ELSE arg_min(ST_AsWKB({geometry}), {ROW_ORDER_REFERENCE}) END"
        )

    def _feature_geometry(self, feature: FeatureConfig) -> str:
        """Resolve the feature geometry expression in the gazetteer CRS."""
        geometry = self._resolve(feature, feature.geometry, "geometry")
        native_crs = self._source_crs(feature.source)
        if native_crs != self.config.crs:
            geometry = (
                f"ST_Transform({geometry}, {quote_literal(native_crs)}, "
                f"{quote_literal(self.config.crs)}, always_xy := true)"
            )
        return geometry

    def _source_crs(self, source_name: str) -> str:
        """Return the CRS of a source, defaulting to the gazetteer CRS."""
        source = self._sources[source_name]
        return source.crs or self.config.crs

    def _first(self, value: str) -> str:
        """Wrap a data value in the first-row aggregate."""
        return f"arg_min({value}, {ROW_ORDER_REFERENCE})"

    def _resolve(self, feature: FeatureConfig, value: str, context: str) -> str:
        """
        Resolve a column-or-expression reference over the joined relation.

        A bare identifier must name a column of the block's source (otherwise it
        is a typo and we fail with a helpful hint) and is qualified to ``src``.
        Anything else is a scalar SQL expression or a qualified reference
        (``<source>.<column>``); its bare identifiers are qualified to ``src``
        and it is passed through, so references to joined sources are the
        author's responsibility.
        """
        base_columns = set(self.catalog[feature.source])
        if _BARE_IDENTIFIER.match(value):
            if value not in base_columns:
                raise CompileError(
                    f"Feature '{feature.source}': {context} references unknown "
                    f"column '{value}' of source '{feature.source}'. "
                    f"{self._available_hint(base_columns)}"
                )
            return f"src.{quote_identifier(value)}"
        replacements = {column: f'src."{column}"' for column in base_columns}
        return f"({qualify_expression(value, replacements)})"

    def _available_hint(self, columns: t.Set[str]) -> str:
        """Build an error message hint listing the available columns."""
        return f"Available columns: {', '.join(sorted(columns))}"
