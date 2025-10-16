from typing import Any, Dict

import sqlalchemy as sa
from sqlmodel import Session

from geoparser.db.crud.gazetteer import GazetteerRepository
from geoparser.db.crud.source import SourceRepository
from geoparser.db.engine import engine
from geoparser.db.models.source import SourceCreate
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

        # Ensure Source record exists
        source_record = self._ensure_source_record(
            registration_table,
            source.features.identifier[0].column,
        )

        self._register_features(source, source_record.id)
        self._register_names(source, source_record.id)

    def _ensure_source_record(self, table_name: str, location_id_name: str):
        """
        Ensure a Source record exists in the database.

        Creates a new source record if it doesn't already exist.

        Args:
            table_name: Name of the table or view
            location_id_name: Name of the location identifier column

        Returns:
            Source record
        """
        with Session(engine) as db:
            # Get gazetteer record
            gazetteer_record = GazetteerRepository.get_by_name(db, self.gazetteer_name)

            # Try to get existing source
            source_record = SourceRepository.get_by_gazetteer_and_name(
                db, gazetteer_record.id, table_name
            )

            if source_record is None:
                source_create = SourceCreate(
                    name=table_name,
                    location_id_name=location_id_name,
                    gazetteer_id=gazetteer_record.id,
                )
                source_record = SourceRepository.create(db, source_create)

            return source_record

    def _register_features(self, source: SourceConfig, source_id: int) -> None:
        """
        Register features from a source.

        Args:
            source: Source configuration
            source_id: ID of the source record
        """
        insert_sql = self.builder.build_feature_insert(source, source_id)

        with create_progress_bar(
            1,
            f"Registering {source.name}",
            "source",
        ) as pbar:
            with engine.connect() as connection:
                connection.execute(sa.text(insert_sql))
                connection.commit()
            pbar.update(1)

    def _register_names(self, source: SourceConfig, source_id: int) -> None:
        """
        Register names from a source.

        Args:
            source: Source configuration
            source_id: ID of the source record
        """
        for name_config in source.features.names:
            name_column = name_config.column
            separator = name_config.separator

            # Choose appropriate insert builder
            if separator:
                insert_sql = self.builder.build_name_insert_separated(
                    source,
                    source_id,
                    name_column,
                    separator,
                )
            else:
                insert_sql = self.builder.build_name_insert(
                    source,
                    source_id,
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
