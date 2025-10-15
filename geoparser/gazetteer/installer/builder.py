import sqlalchemy as sa
from tqdm.auto import tqdm

from geoparser.db.engine import engine
from geoparser.gazetteer.installer.generator import SQLGenerator
from geoparser.gazetteer.model import DataType, SourceConfig


class SchemaBuilder:
    """Builds database schema (tables and views) for gazetteers."""

    # Suffix appended to source names to create view names
    VIEW_SUFFIX = "_view"

    def __init__(self):
        self.generator = SQLGenerator()

    def create_table(self, source_config: SourceConfig) -> str:
        """
        Create a table with appropriate columns and constraints.

        Args:
            source_config: Source configuration

        Returns:
            The created table name
        """
        table_name = source_config.name

        # Drop existing table using SpatiaLite cleanup
        with engine.connect() as connection:
            try:
                connection.execute(
                    sa.text(f"SELECT DropTable(NULL, '{table_name}', 1)")
                )
            except sa.exc.DatabaseError:
                # Fall back to regular DROP TABLE if DropTable fails
                # (e.g., table doesn't exist or isn't a spatial table)
                connection.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.commit()

        # Build column definitions
        columns = []

        # Add original attribute columns (excluding dropped ones)
        for attr in source_config.attributes.original:
            if not attr.drop:
                if attr.type == DataType.GEOMETRY:
                    # Geometry columns start as TEXT with _wkt suffix
                    columns.append(f"{attr.name}_wkt TEXT")
                else:
                    columns.append(f"{attr.name} {attr.type.value}")

        # Add derived attribute columns
        for attr in source_config.attributes.derived:
            if attr.type == DataType.GEOMETRY:
                # Geometry columns start as TEXT with _wkt suffix
                columns.append(f"{attr.name}_wkt TEXT")
            else:
                columns.append(f"{attr.name} {attr.type.value}")

        # Create the table
        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"

        with engine.connect() as connection:
            connection.execute(sa.text(create_table_sql))
            connection.commit()

        # Dispose engine to clear connection pool after table creation.
        # This ensures that subsequent operations start with a fresh connection
        # and properly see the newly created table structure.
        engine.dispose()

        return table_name

    def create_view(self, source_config: SourceConfig) -> str:
        """
        Create a SQL view based on source view configuration.

        Args:
            source_config: Source configuration with view definition

        Returns:
            The created view name
        """
        if source_config.view is None:
            raise ValueError(f"Source '{source_config.name}' has no view configuration")

        # View name is source name with VIEW_SUFFIX
        view_name = f"{source_config.name}{self.VIEW_SUFFIX}"

        with tqdm(
            total=1,
            desc=f"Creating view {view_name}",
            unit="view",
        ) as pbar:
            with engine.connect() as connection:
                # Drop existing view
                connection.execute(sa.text(f"DROP VIEW IF EXISTS {view_name}"))

                # Generate and execute view SQL
                view_sql = self.generator.build_view_sql(source_config, view_name)
                connection.execute(sa.text(view_sql))
                connection.commit()

            pbar.update(1)

        return view_name
