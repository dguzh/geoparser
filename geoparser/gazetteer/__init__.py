import typing as t

from geoparser.gazetteer.feature import Feature
from geoparser.gazetteer.gazetteer import Gazetteer

if t.TYPE_CHECKING:
    from geoparser.gazetteer.build import GazetteerBuilder

__all__ = ["Feature", "Gazetteer", "GazetteerBuilder"]


def __getattr__(name: str) -> object:
    """
    Resolve ``GazetteerBuilder`` on first use.

    Building a gazetteer is a one-off administrative task, while looking places
    up in one happens on every parse. Importing the build pipeline eagerly made
    every ``import geoparser`` pay for duckdb and the config schema, so it is
    loaded only when actually referenced.

    Args:
        name: Attribute being looked up

    Returns:
        The requested attribute

    Raises:
        AttributeError: If the name is not exported by this package
    """
    if name == "GazetteerBuilder":
        from geoparser.gazetteer.build import GazetteerBuilder

        return GazetteerBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
