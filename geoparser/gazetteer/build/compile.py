"""
Projection compiler: turns feature blocks into DuckDB SQL.

Each feature block compiles into:

- one *feature query* producing ``(identifier, type, attributes, geometry)``
  rows, where rows sharing an identifier are merged according to the block's
  merge policy (names collected, geometry first/union, attributes by policy)
- one or more *name queries* producing ``(identifier, text)`` rows from the
  block's name specs (own columns, expressions, split multi-value fields, or
  rows of a related input keyed by the feature identifier)

Both kinds of query select from an *enriched* relation: the feature's input
left-joined against its lookups, exposing lookup values as plain columns.
"""

import re
import typing as t

from geoparser.gazetteer.build.stage import (
    GEOMETRY_COLUMN,
    quote_identifier,
    quote_literal,
)
from geoparser.gazetteer.config import (
    AttributeMerge,
    FeatureConfig,
    GazetteerConfig,
    GeometryMerge,
    GeometryTransform,
    NameConfig,
    SpatialPredicate,
)

# Internal column carrying the input row order, used for deterministic
# "first" merge semantics.
ROW_ORDER_COLUMN = "_rid"

_BARE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_SPATIAL_FUNCTIONS = {
    SpatialPredicate.WITHIN: "ST_Within",
    SpatialPredicate.INTERSECTS: "ST_Intersects",
    SpatialPredicate.CONTAINS: "ST_Contains",
}

# Matches string literals, quoted identifiers and bare identifiers so
# expressions can be scanned token by token.
_EXPRESSION_TOKEN = re.compile(
    r"'(?:[^']|'')*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_]*"
)


def qualify_expression(expression: str, replacements: t.Mapping[str, str]) -> str:
    """
    Replace bare column references in a scalar SQL expression.

    Used for expressions evaluated in a join context, where an unqualified
    column name could be ambiguous between the feature's input and a joined
    lookup input. String literals, quoted identifiers, already-qualified
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

    The compiler needs to know the columns of the staged inputs (the catalog)
    to resolve bare column references and detect name clashes between input
    columns and lookup values.
    """

    def __init__(
        self, config: GazetteerConfig, catalog: t.Dict[str, t.List[str]]
    ):
        """
        Initialize the compiler.

        Args:
            config: Validated gazetteer configuration
            catalog: Mapping of staged input names to their column names
        """
        self.config = config
        self.catalog = catalog
        self._inputs = {
            input_config.name: input_config for input_config in config.inputs
        }

    def feature_query(self, feature: FeatureConfig) -> str:
        """
        Compile the feature query for a feature block.

        The query yields one row per distinct identifier with columns
        ``identifier`` (VARCHAR), ``type`` (VARCHAR), ``attributes``
        (JSON text) and ``geometry`` (WKB blob or NULL).

        Args:
            feature: Feature block to compile

        Returns:
            DuckDB SQL string
        """
        enriched, available = self._enriched_relation(feature)
        identifier = self._reference(feature.identifier, available)

        attribute_parts = []
        for attribute in feature.attributes:
            if attribute.expression:
                value = self._reference(attribute.expression, available)
            else:
                if attribute.column not in available:
                    raise CompileError(
                        f"Feature '{feature.type}': attribute '{attribute.name}' "
                        f"references unknown column '{attribute.column}'. "
                        f"{self._available_hint(available)}"
                    )
                value = quote_identifier(attribute.column)
            policy = attribute.merge or feature.merge.attributes
            attribute_parts.append(
                f"{quote_literal(attribute.name)}: {self._aggregate(value, policy)}"
            )
        if attribute_parts:
            attributes_sql = (
                f"CAST(to_json({{{', '.join(attribute_parts)}}}) AS VARCHAR)"
            )
        else:
            attributes_sql = "'{}'"

        geometry_sql = self._geometry_select(feature, available)

        return (
            f"WITH enriched AS ({enriched})\n"
            f"SELECT\n"
            f"    CAST(({identifier}) AS VARCHAR) AS identifier,\n"
            f"    {quote_literal(feature.type)} AS type,\n"
            f"    {attributes_sql} AS attributes,\n"
            f"    {geometry_sql} AS geometry\n"
            f"FROM enriched\n"
            f"WHERE ({identifier}) IS NOT NULL\n"
            f"GROUP BY 1"
        )

    def name_queries(self, feature: FeatureConfig) -> t.List[str]:
        """
        Compile the name queries for a feature block.

        Each query yields ``(identifier, text)`` rows with trimmed, non-empty
        name strings.

        Args:
            feature: Feature block to compile

        Returns:
            List of DuckDB SQL strings
        """
        enriched, available = self._enriched_relation(feature)
        identifier = self._reference(feature.identifier, available)

        queries = []
        for name in feature.names:
            if name.from_ is not None:
                queries.append(self._related_name_query(feature, name))
            else:
                value = self._name_value(feature, name, available)
                part = self._split_part(value, name.split)
                queries.append(
                    f"WITH enriched AS ({enriched})\n"
                    f"SELECT DISTINCT identifier, trim(part) AS text\n"
                    f"FROM (\n"
                    f"    SELECT CAST(({identifier}) AS VARCHAR) AS identifier, "
                    f"{part} AS part\n"
                    f"    FROM enriched\n"
                    f"    WHERE ({identifier}) IS NOT NULL\n"
                    f")\n"
                    f"WHERE part IS NOT NULL AND trim(part) <> ''"
                )
        return queries

    def _name_value(
        self, feature: FeatureConfig, name: NameConfig, available: t.Set[str]
    ) -> str:
        """Resolve the value expression of an inline name spec."""
        if name.expression:
            return self._reference(name.expression, available)
        if name.column not in available:
            raise CompileError(
                f"Feature '{feature.type}': name references unknown column "
                f"'{name.column}'. {self._available_hint(available)}"
            )
        return quote_identifier(name.column)

    def _related_name_query(self, feature: FeatureConfig, name: NameConfig) -> str:
        """Compile a name query against a related input."""
        related_columns = set(self.catalog[name.from_])
        if name.key not in related_columns:
            raise CompileError(
                f"Feature '{feature.type}': name key '{name.key}' is not a column "
                f"of input '{name.from_}'"
            )
        if name.expression:
            value = name.expression
        else:
            if name.column not in related_columns:
                raise CompileError(
                    f"Feature '{feature.type}': name column '{name.column}' is not "
                    f"a column of input '{name.from_}'"
                )
            value = quote_identifier(name.column)
        part = self._split_part(value, name.split)
        return (
            f"SELECT DISTINCT identifier, trim(part) AS text\n"
            f"FROM (\n"
            f"    SELECT CAST({quote_identifier(name.key)} AS VARCHAR) "
            f"AS identifier, {part} AS part\n"
            f"    FROM {quote_identifier(name.from_)}\n"
            f"    WHERE {quote_identifier(name.key)} IS NOT NULL\n"
            f")\n"
            f"WHERE part IS NOT NULL AND trim(part) <> ''"
        )

    def _split_part(self, value: str, split: t.Optional[str]) -> str:
        """Wrap a name value in a split/unnest when a separator is configured."""
        value = f"CAST(({value}) AS VARCHAR)"
        if split is None:
            return value
        return f"unnest(string_split({value}, {quote_literal(split)}))"

    def _enriched_relation(
        self, feature: FeatureConfig
    ) -> t.Tuple[str, t.Set[str]]:
        """
        Build the enriched SELECT for a feature block.

        Returns the SQL of the enriched relation (feature input left-joined
        against its lookups, lookup values exposed as plain columns) and the
        set of column names available on it.
        """
        base_columns = list(self.catalog[feature.from_])

        # Resolve lookup joins in order; values of earlier lookups are
        # available as join keys for later ones.
        joins: t.List[str] = []
        value_refs: t.Dict[str, str] = {}
        value_selects: t.List[str] = []
        for index, lookup_name in enumerate(feature.lookups):
            lookup = self.config.lookups[lookup_name]
            alias = f"lk{index}"
            condition = self._lookup_condition(
                feature, lookup_name, alias, value_refs, base_columns
            )
            joins.append(
                f"LEFT JOIN {quote_identifier(lookup.from_)} AS {alias} "
                f"ON {condition}"
            )
            lookup_columns = set(self.catalog[lookup.from_])
            for value_name, value_column in lookup.values.items():
                if value_column not in lookup_columns:
                    raise CompileError(
                        f"Lookup '{lookup_name}': value '{value_name}' references "
                        f"unknown column '{value_column}' of input '{lookup.from_}'"
                    )
                reference = f"{alias}.{quote_identifier(value_column)}"
                value_refs[value_name] = reference
                value_selects.append(
                    f"{reference} AS {quote_identifier(value_name)}"
                )

        # Lookup values shadow base columns of the same name
        shadowed = [column for column in base_columns if column in value_refs]
        if shadowed:
            exclusion = ", ".join(quote_identifier(column) for column in shadowed)
            base_select = f"src.* EXCLUDE ({exclusion})"
        else:
            base_select = "src.*"

        select_parts = [f"src.rowid AS {ROW_ORDER_COLUMN}", base_select]
        select_parts.extend(value_selects)

        sql_parts = [
            f"SELECT {', '.join(select_parts)}",
            f"FROM {quote_identifier(feature.from_)} AS src",
        ]
        sql_parts.extend(joins)
        enriched_sql = "\n".join(sql_parts)

        available = set(base_columns) | set(value_refs) | {ROW_ORDER_COLUMN}
        return enriched_sql, available

    def _lookup_condition(
        self,
        feature: FeatureConfig,
        lookup_name: str,
        alias: str,
        value_refs: t.Dict[str, str],
        base_columns: t.List[str],
    ) -> str:
        """Build the join condition of a lookup."""
        lookup = self.config.lookups[lookup_name]
        lookup_columns = set(self.catalog[lookup.from_])
        match = lookup.match

        if match.on:
            conditions = []
            for left_key, right_column in match.on.items():
                if right_column not in lookup_columns:
                    raise CompileError(
                        f"Lookup '{lookup_name}': match references unknown column "
                        f"'{right_column}' of input '{lookup.from_}'"
                    )
                if left_key in value_refs:
                    left_reference = value_refs[left_key]
                elif left_key in base_columns:
                    left_reference = f"src.{quote_identifier(left_key)}"
                elif not _BARE_IDENTIFIER.match(left_key):
                    # Scalar expression over the feature's input columns and
                    # earlier lookup values; qualify bare references to avoid
                    # ambiguity with columns of joined lookup inputs
                    replacements = dict(value_refs)
                    for column in base_columns:
                        replacements.setdefault(column, f'src."{column}"')
                    left_reference = f"({qualify_expression(left_key, replacements)})"
                else:
                    raise CompileError(
                        f"Feature '{feature.type}': lookup '{lookup_name}' matches "
                        f"on '{left_key}', which is neither a column of input "
                        f"'{feature.from_}' nor a value of an earlier lookup"
                    )
                conditions.append(
                    f"{left_reference} = {alias}.{quote_identifier(right_column)}"
                )
            return " AND ".join(conditions)

        # Spatial match against the lookup input's geometry
        if GEOMETRY_COLUMN not in lookup_columns:
            raise CompileError(
                f"Lookup '{lookup_name}': input '{lookup.from_}' has no geometry "
                "column to match against"
            )
        left_geometry = self._native_geometry(feature, qualified=True)
        if match.using == GeometryTransform.CENTROID:
            left_geometry = f"ST_Centroid({left_geometry})"
        left_crs = self._feature_geometry_crs(feature)
        right_crs = self._input_crs(lookup.from_)
        if left_crs != right_crs:
            left_geometry = (
                f"ST_Transform({left_geometry}, {quote_literal(left_crs)}, "
                f"{quote_literal(right_crs)}, always_xy := true)"
            )
        function = _SPATIAL_FUNCTIONS[match.spatial]
        return (
            f"{function}({left_geometry}, "
            f"{alias}.{quote_identifier(GEOMETRY_COLUMN)})"
        )

    def _geometry_select(
        self, feature: FeatureConfig, available: t.Set[str]
    ) -> str:
        """Build the aggregated geometry expression in the gazetteer CRS."""
        if feature.geometry is None:
            return "NULL"
        geometry = self._native_geometry(feature, qualified=False, available=available)
        native_crs = self._feature_geometry_crs(feature)
        if native_crs != self.config.crs:
            geometry = (
                f"ST_Transform({geometry}, {quote_literal(native_crs)}, "
                f"{quote_literal(self.config.crs)}, always_xy := true)"
            )
        if feature.merge.geometry == GeometryMerge.UNION:
            return f"ST_AsWKB(ST_Union_Agg({geometry}))"
        return f"ST_AsWKB(arg_min({geometry}, {ROW_ORDER_COLUMN}))"

    def _native_geometry(
        self,
        feature: FeatureConfig,
        qualified: bool,
        available: t.Optional[t.Set[str]] = None,
    ) -> str:
        """
        Build the feature geometry expression in its native CRS.

        Args:
            feature: Feature block
            qualified: Whether references must be qualified with the ``src``
                alias (required inside join conditions)
            available: Available column names when unqualified

        Returns:
            Geometry SQL expression
        """
        if feature.geometry is None:
            raise CompileError(
                f"Feature '{feature.type}' uses a spatial lookup but defines "
                "no geometry"
            )
        base_columns = set(self.catalog[feature.from_])
        scope = base_columns if qualified else (available or base_columns)

        def resolve(reference: str) -> str:
            if _BARE_IDENTIFIER.match(reference) and reference in scope:
                column = quote_identifier(reference)
                return f"src.{column}" if qualified else column
            if _BARE_IDENTIFIER.match(reference):
                raise CompileError(
                    f"Feature '{feature.type}': geometry references unknown "
                    f"column '{reference}' of input '{feature.from_}'"
                )
            return f"({reference})"

        if feature.geometry.column:
            return resolve(feature.geometry.column)
        point = feature.geometry.point
        lon = resolve(point.lon)
        lat = resolve(point.lat)
        return (
            f"CASE WHEN {lon} IS NOT NULL AND {lat} IS NOT NULL "
            f"THEN ST_Point({lon}, {lat}) END"
        )

    def _feature_geometry_crs(self, feature: FeatureConfig) -> str:
        """Return the native CRS of a feature's geometry."""
        if feature.geometry is not None and feature.geometry.crs:
            return feature.geometry.crs
        return self._input_crs(feature.from_)

    def _input_crs(self, input_name: str) -> str:
        """Return the CRS of an input, defaulting to the gazetteer CRS."""
        input_config = self._inputs[input_name]
        return input_config.crs or self.config.crs

    def _aggregate(self, value: str, policy: AttributeMerge) -> str:
        """Wrap an attribute value in its merge aggregate."""
        if policy == AttributeMerge.MIN:
            return f"min({value})"
        if policy == AttributeMerge.MAX:
            return f"max({value})"
        return f"arg_min({value}, {ROW_ORDER_COLUMN})"

    def _reference(self, expression: str, available: t.Set[str]) -> str:
        """
        Resolve a column-or-expression reference over the enriched relation.

        Bare identifiers naming an available column are quoted; anything else
        is treated as a scalar SQL expression and passed through.
        """
        if _BARE_IDENTIFIER.match(expression) and expression in available:
            return quote_identifier(expression)
        return expression

    def _available_hint(self, available: t.Set[str]) -> str:
        """Build an error message hint listing the available columns."""
        columns = sorted(column for column in available if column != ROW_ORDER_COLUMN)
        return f"Available columns: {', '.join(columns)}"
