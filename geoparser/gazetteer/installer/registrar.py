import sqlalchemy as sa
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.installer.generator import SQLGenerator
from geoparser.gazetteer.model import SourceConfig


class FeatureRegistrar:
    """Registers features and names in the database."""

    def __init__(self):
        self.generator = SQLGenerator()

    def register(
        self, source_config: SourceConfig, gazetteer_name: str, view_name: str = None
    ) -> None:
        """
        Register features and names from a source.

        Args:
            source_config: Source configuration with feature definition
            gazetteer_name: Name of the gazetteer
            view_name: Name of the view (or None to use source name)
        """
        if source_config.features is None:
            return

        # Use view name if available, otherwise use source name
        registration_name = view_name if view_name else source_config.name

        # Register features
        self._register_features(source_config, gazetteer_name, registration_name)

        # Register names
        self._register_names(source_config, gazetteer_name, registration_name)

    def _register_features(
        self, source_config: SourceConfig, gazetteer_name: str, registration_name: str
    ) -> None:
        """
        Register features from a source.

        Args:
            source_config: Source configuration
            gazetteer_name: Name of the gazetteer
            registration_name: Name of the table or view to register from
        """
        with tqdm(
            total=1,
            desc=f"Registering features from {source_config.name}",
            unit="source",
        ) as pbar:
            with engine.connect() as connection:
                # Generate and execute feature registration SQL
                sql = self.generator.build_feature_registration_sql(
                    source_config, gazetteer_name, registration_name
                )
                connection.execute(sa.text(sql))
                connection.commit()

            pbar.update(1)

    def _register_names(
        self, source_config: SourceConfig, gazetteer_name: str, registration_name: str
    ) -> None:
        """
        Register names from a source.

        Args:
            source_config: Source configuration
            gazetteer_name: Name of the gazetteer
            registration_name: Name of the table or view to register from
        """
        for name_config in source_config.features.names:
            name_column = name_config.column
            separator = name_config.separator

            with tqdm(
                total=1,
                desc=f"Registering names from {source_config.name}.{name_column}",
                unit="column",
            ) as pbar:
                with engine.connect() as connection:
                    # Generate and execute name registration SQL
                    sql = self.generator.build_name_registration_sql(
                        source_config,
                        gazetteer_name,
                        registration_name,
                        name_column,
                        separator,
                    )
                    connection.execute(sa.text(sql))
                    connection.commit()

                pbar.update(1)
