from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.db import get_connection
from geoparser.gazetteer.installer.model import SourceConfig
from geoparser.gazetteer.installer.queries.ddl import ViewBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.stages.schema import VIEW_SUFFIX
from geoparser.gazetteer.installer.utils.progress import create_progress_bar


class ViewStage(Stage):
    """
    Creates database views for gazetteer sources.

    Views are created after geometries are built and spatial joins are
    precomputed, so spatial joins can be expressed as plain equality joins
    on the precomputed key columns.
    """

    def __init__(self):
        """Initialize the view stage with a query builder."""
        super().__init__(
            name="View",
            description="Create database views",
        )
        self.view_builder = ViewBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Create the view for a source, if it defines one.

        Args:
            source: Source configuration
            context: Shared context (will be populated with 'view_name')
        """
        view_name = None
        if source.view:
            view_name = self._create_view(source)

        context["view_name"] = view_name

    def _create_view(self, source: SourceConfig) -> str:
        """
        Create a view for a source.

        Args:
            source: Source configuration with view definition

        Returns:
            Name of the created view
        """
        view_name = f"{source.name}{VIEW_SUFFIX}"

        with create_progress_bar(1, f"Creating {view_name}", "view") as pbar:
            create_sql = self.view_builder.build_create_view(source, view_name)

            with get_connection() as connection:
                connection.execute(sa.text(f"DROP VIEW IF EXISTS {view_name}"))
                connection.execute(sa.text(create_sql))
                connection.commit()

            pbar.update(1)

        return view_name
