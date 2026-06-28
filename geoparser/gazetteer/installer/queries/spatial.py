from geoparser.gazetteer.installer.model import SpatialConditionConfig

# Prefix for precomputed spatial-join key columns added to the left table.
SPATIAL_JOIN_COLUMN_PREFIX = "__spatial_join_"


def spatial_join_column_name(right_source: str) -> str:
    """
    Build the name of the precomputed spatial-join key column.

    Spatial joins are precomputed at install time: for each row of the left
    table, the matching right-table ``rowid`` is stored in this column. The
    view then joins on plain equality instead of a spatial predicate.

    Args:
        right_source: Name of the right-hand (joined) source/table

    Returns:
        Column name used to store the matched right-table rowid
    """
    return f"{SPATIAL_JOIN_COLUMN_PREFIX}{right_source}"


def build_spatial_equality_condition(condition: SpatialConditionConfig) -> str:
    """
    Build the plain SQL equality condition for a precomputed spatial join.

    Translates a spatial join condition into an equality between the
    precomputed key column on the left table and the right table's rowid.

    Args:
        condition: Spatial join condition

    Returns:
        SQL join condition (without the ON keyword)
    """
    column = spatial_join_column_name(condition.right_source)
    return f"{condition.left_source}.{column} = {condition.right_source}.rowid"
