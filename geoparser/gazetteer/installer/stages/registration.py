from typing import Any, Dict

import sqlalchemy as sa

from geoparser.db.engine import engine
from geoparser.gazetteer.installer.queries.dml import FeatureRegistrationBuilder
from geoparser.gazetteer.installer.stages.base import Stage
from geoparser.gazetteer.installer.utils.progress import create_progress_bar
from geoparser.gazetteer.model import SourceConfig


class RegistrationStage(Stage):
    """
    Registers features and names in the database.

    This stage extracts features and names from source tables and
    registers them in the main feature and name tables for lookup.
    """

    def __init__(self, gazetteer_name: str):
        """
        Initialize the registration stage.

        Args:
            gazetteer_name: Name of the gazetteer being installed
        """
        super().__init__(
            name="Registration",
            description="Register features and names",
        )
        self.gazetteer_name = gazetteer_name
        self.builder = FeatureRegistrationBuilder()

    def execute(self, source: SourceConfig, context: Dict[str, Any]) -> None:
        """
        Register features and names for a source.

        Args:
            source: Source configuration
            context: Shared context (must contain 'table_name' and 'view_name')
        """
        if source.features is None:
            return

        # Use view name if available, otherwise use table name
        registration_table = context.get("view_name") or context["table_name"]

        self._register_features(source, registration_table)
        self._register_names(source, registration_table)

    def _register_features(self, source: SourceConfig, registration_table: str) -> None:
        """
        Register features from a source.

        Args:
            source: Source configuration
            registration_table: Name of the table or view to register from
        """
        insert_sql = self.builder.build_feature_insert(
            source, self.gazetteer_name, registration_table
        )

        with create_progress_bar(
            1,
            f"Registering {source.name}",
            "source",
        ) as pbar:
            with engine.connect() as connection:
                connection.execute(sa.text(insert_sql))
                connection.commit()
            pbar.update(1)

    def _register_names(self, source: SourceConfig, registration_table: str) -> None:
        """
        Register names from a source.

        Args:
            source: Source configuration
            registration_table: Name of the table or view to register from
        """
        for name_config in source.features.names:
            name_column = name_config.column
            separator = name_config.separator

            # Choose appropriate insert builder
            if separator:
                insert_sql = self.builder.build_name_insert_separated(
                    source,
                    self.gazetteer_name,
                    registration_table,
                    name_column,
                    separator,
                )
            else:
                insert_sql = self.builder.build_name_insert(
                    source,
                    self.gazetteer_name,
                    registration_table,
                    name_column,
                )

            # Execute registration
            with create_progress_bar(
                1,
                f"Registering {source.name}.{name_column}",
                "column",
            ) as pbar:
                with engine.connect() as connection:
                    connection.execute(sa.text(insert_sql))
                    connection.commit()
                pbar.update(1)
