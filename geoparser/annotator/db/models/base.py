"""Package-owned SQLModel registry for the annotator database.

Kept separate from ``SQLModel.metadata`` and from the core Geoparser registry
so each database is created from its own tables only.
"""

from sqlalchemy.orm import registry
from sqlmodel import SQLModel

annotator_registry = registry()


class AnnotatorModel(SQLModel, registry=annotator_registry):
    """Abstract base for annotator persistence models."""
