"""Package-owned SQLModel registry for the core database.

``SQLModel.metadata`` is process-global. Creating tables from it would also
create tables registered by a host application that uses SQLModel, and a host
``create_all`` would create Geoparser tables in the host database.
"""

from sqlalchemy.orm import registry
from sqlmodel import SQLModel

geoparser_registry = registry()


class GeoparserModel(SQLModel, registry=geoparser_registry):
    """Abstract base for core persistence models."""
