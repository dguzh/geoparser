from __future__ import annotations

import math
import os
import re
import shutil
import sqlite3
import typing as t
import zipfile
from abc import ABC, abstractmethod
from difflib import get_close_matches
from threading import local

import pandas as pd
import requests
from appdirs import user_data_dir
from tqdm.auto import tqdm

from geoparser.config import get_gazetteer_configs
from geoparser.config.models import GazetteerData


class Gazetteer(ABC):
    """Abstract base class for gazetteers."""

    @abstractmethod
    def _create_location_description(self, location: t.Dict[str, t.Any]) -> str:
        """
        Create a textual description for a location.

        Args:
            location (Dict[str, Any]): Dictionary containing location attributes.

        Returns:
            str: Textual description of the location.
        """
        pass

    def get_location_description(self, location: t.Dict[str, t.Any]) -> str:
        """
        Get the location description by invoking the abstract method.

        Args:
            location (Dict[str, Any]): Dictionary containing location attributes.

        Returns:
            str: Textual description of the location.
        """
        return self._create_location_description(location)


class LocalDBGazetteer(Gazetteer):
    """Gazetteer implementation using a local SQLite database."""

    def __init__(self, gazetteer_name: str):
        """
        Initialize the LocalDBGazetteer.

        Args:
            gazetteer_name (str): Name of the gazetteer.
        """
        super().__init__()
        self.data_dir = os.path.join(user_data_dir("geoparser", ""), gazetteer_name)
        self.db_path = os.path.join(self.data_dir, gazetteer_name + ".db")
        self.config = get_gazetteer_configs()[gazetteer_name]
        self._local = local()
        self._filter_cache = {}

    def connect(func: t.Callable) -> t.Callable:
        """
        Decorator to initiate a database connection before a function call.

        Args:
            func (Callable): Function to wrap.

        Returns:
            Callable: Wrapped function with database connection.
        """

        def call(self, *args, **kwargs):
            self._initiate_connection()
            ret = func(self, *args, **kwargs)
            return ret

        return call

    def commit(func: t.Callable) -> t.Callable:
        """
        Decorator to commit changes to the database after a function call.

        Args:
            func (Callable): Function to wrap.

        Returns:
            Callable: Wrapped function with database commit.
        """

        def call(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self._commit()
            return ret

        return call

    def close(func: t.Callable) -> t.Callable:
        """
        Decorator to close the database connection after a function call.

        Args:
            func (Callable): Function to wrap.

        Returns:
            Callable: Wrapped function with database closure.
        """

        def call(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self._close_connection()
            return ret

        return call

    def _initiate_connection(self) -> None:
        """
        Initiate a new database connection if one doesn't exist.
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)

    def _close_connection(self) -> None:
        """
        Close the existing database connection.
        """
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            self._local.conn = None

    def _commit(self) -> None:
        """
        Commit the current transaction to the database.
        """
        self._local.conn.commit()

    def _get_cursor(self) -> sqlite3.Cursor:
        """
        Get a cursor from the current database connection.

        Returns:
            sqlite3.Cursor: Database cursor object.
        """
        return self._local.conn.cursor()

    @close
    @connect
    def execute_query(
        self, query: str, params: t.Optional[tuple] = None
    ) -> t.List[t.Any]:
        """
        Execute a SQL query and fetch all results.

        Args:
            query (str): SQL query to execute.
            params (Optional[tuple], optional): Parameters for the SQL query.

        Returns:
            List[Any]: List of query results.
        """
        cursor = self._get_cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()

    def setup_database(self) -> None:
        """
        Set up the database by downloading and loading data.
        """
        print("Database setup...")

        self.clean_dir()

        os.makedirs(self.data_dir, exist_ok=True)

        for dataset in self.config.data:
            self._download_file(dataset)
            self._load_data(dataset)

        self._create_names_table()
        self._populate_names_table()

        self._create_names_fts_table()
        self._populate_names_fts_table()

        self._create_locations_table()
        self._populate_locations_table()

        for attribute in self._get_filter_attributes():
            self._create_values_table(attribute)
            self._populate_values_table(attribute)

        self._drop_redundant_tables()

        self.clean_dir(keep_db=True)

        print("Database setup complete.")

    def clean_dir(self, keep_db: bool = False) -> None:
        """
        Clean the data directory by removing unnecessary files.

        Args:
            keep_db (bool, optional): Whether to keep the database files. Defaults to False.
        """
        if os.path.exists(self.data_dir):
            for file_name in os.listdir(self.data_dir):
                if keep_db and (
                    file_name.endswith(".db") or file_name.endswith(".db-journal")
                ):
                    continue
                else:
                    try:
                        os.remove(os.path.join(self.data_dir, file_name))
                    except (IsADirectoryError, PermissionError):
                        shutil.rmtree(os.path.join(self.data_dir, file_name))

    @close
    @commit
    @connect
    def _drop_redundant_tables(self) -> None:
        """
        Drop redundant tables from the database and perform vacuuming.
        """
        cursor = self._get_cursor()
        tables_to_drop = [dataset.name for dataset in self.config.data]
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
        cursor.execute("VACUUM;")

    def _download_file(self, dataset: GazetteerData) -> None:
        """
        Download dataset files if they do not exist locally.

        Args:
            dataset (GazetteerData): Dataset configuration object.
        """
        url = dataset.url
        filename = url.split("/")[-1]
        file_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(file_path):
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as f, tqdm(
                desc=f"Downloading {filename}",
                total=int(response.headers.get("content-length", 0)),
                unit="iB",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    size = f.write(chunk)
                    bar.update(size)
        if file_path.endswith(".zip"):
            self._extract_zip(file_path, dataset.extracted_files)

    def _extract_zip(self, file_path: str, extracted_files: t.List[str]) -> None:
        """
        Extract specific files from a zip archive.

        Args:
            file_path (str): Path to the zip file.
            extracted_files (List[str]): List of files to extract.
        """
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            for file_name in extracted_files:
                zip_ref.extract(file_name, self.data_dir)

    def _load_data(self, dataset: GazetteerData) -> None:
        """
        Load data from the dataset into the database.

        Args:
            dataset (GazetteerData): Dataset configuration object.
        """
        self._create_data_table(dataset)
        self._populate_data_table(dataset)

    @abstractmethod
    def _read_file(
        self,
        file_path: str,
        columns: t.List[str] = None,
        skiprows: t.Union[int, t.List[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
        """
        Read a file and yield data in chunks.

        Args:
            file_path (str): Path to the file.
            columns (List[str], optional): List of columns to read.
            skiprows (Union[int, List[int], Callable], optional): Rows to skip.
            chunksize (int, optional): Number of rows per chunk.

        Yields:
            Iterator[pd.DataFrame]: Iterator over DataFrame chunks.
        """
        pass

    @close
    @commit
    @connect
    def _create_data_table(self, dataset: GazetteerData) -> None:
        """
        Create a data table in the database for the dataset.

        Args:
            dataset (GazetteerData): Dataset configuration object.
        """
        cursor = self._get_cursor()
        columns = ", ".join(
            [
                f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
                for col in dataset.columns
            ]
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {dataset.name} ({columns})")

    @close
    @commit
    @connect
    def _populate_data_table(self, dataset: GazetteerData) -> None:
        """
        Populate the data table with dataset content.

        Args:
            dataset (GazetteerData): Dataset configuration object.
        """
        file_path = os.path.join(self.data_dir, dataset.extracted_files[0])
        table_name = dataset.name
        columns = [col.name for col in dataset.columns]
        skiprows = dataset.skiprows
        chunksize = 100000

        chunks, n_chunks = self._read_file(file_path, columns, skiprows, chunksize)

        for chunk in tqdm(
            chunks,
            desc=f"Loading {table_name}",
            total=n_chunks,
        ):
            chunk.to_sql(table_name, self._local.conn, if_exists="append", index=False)

    @close
    @commit
    @connect
    def _create_names_table(self) -> None:
        """
        Create the 'names' table in the database.
        """
        location_identifier_type = [
            c.type
            for c in self.config.location_columns
            if c.name == self.config.location_identifier
        ][0]
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {self.config.location_identifier} {location_identifier_type},
                name TEXT
            )
        """
        )

    @close
    @commit
    @connect
    def _populate_names_table(self, chunksize: int = 100000) -> None:
        """
        Populate the 'names' table with location names.

        Args:
            chunksize (int, optional): Number of rows per chunk. Defaults to 100000.
        """
        for dataset in self.config.data:
            if dataset.toponym_columns:

                toponym_columns = dataset.toponym_columns
                location_identifier = self.config.location_identifier

                columns_to_select = [location_identifier] + [
                    tc.name for tc in toponym_columns
                ]

                query = f'SELECT {", ".join(columns_to_select)} FROM {dataset.name}'

                cursor = self._local.conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {dataset.name}")
                total_rows = cursor.fetchone()[0]
                total_chunks = math.ceil(total_rows / chunksize)

                chunks = pd.read_sql_query(query, self._local.conn, chunksize=chunksize)

                for chunk in tqdm(
                    chunks,
                    desc=f"Loading names from {dataset.name}",
                    total=total_chunks,
                ):
                    chunk[location_identifier] = chunk[location_identifier].astype(str)

                    name_dfs = []

                    for tc in toponym_columns:
                        name = tc.name

                        df = chunk[[location_identifier, name]].dropna()

                        if tc.separator:
                            separator = tc.separator
                            df[name] = df[name].str.split(separator)
                            df = df.explode(name)

                        df = df.rename(columns={name: "name"})
                        df = df[[location_identifier, "name"]]

                        if tc.geoqualifier_pattern:
                            pattern = re.compile(tc.geoqualifier_pattern)

                            stripped_df = df.copy()
                            stripped_df["name"] = stripped_df["name"].apply(
                                lambda n: (
                                    pattern.sub("", n).strip()
                                    if isinstance(n, str)
                                    else n
                                )
                            )

                            df = pd.concat([df, stripped_df], ignore_index=True)
                            df = df.drop_duplicates(
                                subset=[location_identifier, "name"]
                            )

                        name_dfs.append(df)

                    if name_dfs:
                        names_df = pd.concat(name_dfs, ignore_index=True)
                        names_df["name"] = names_df["name"].str.strip()
                        names_df = names_df[names_df["name"] != ""]

                        names_df.to_sql(
                            "names",
                            self._local.conn,
                            if_exists="append",
                            index=False,
                            method="multi",
                            chunksize=400,
                        )

    @close
    @commit
    @connect
    def _create_names_fts_table(self) -> None:
        """
        Create the full-text search virtual table 'names_fts'.
        """
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS names_fts USING fts5(
                name,
                {self.config.location_identifier} UNINDEXED,
                content='names',
                content_rowid='id',
                tokenize="unicode61 tokenchars '.'"
            )
        """
        )

    @close
    @commit
    @connect
    def _populate_names_fts_table(self) -> None:
        """
        Populate the 'names_fts' full-text search table.
        """
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            INSERT INTO names_fts (rowid, name, {self.config.location_identifier})
            SELECT id, name, {self.config.location_identifier} FROM names
        """
        )

    @close
    @commit
    @connect
    def _create_locations_table(self) -> None:
        """
        Create the 'locations' table in the database.
        """
        columns = self.config.location_columns
        cursor = self._get_cursor()
        columns_def = ", ".join(
            f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
            for col in columns
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS locations ({columns_def})")

    @abstractmethod
    def _populate_locations_table(self) -> None:
        """
        Populate the 'locations' table with location data.
        """
        pass

    @close
    @commit
    @connect
    def _create_values_table(self, attribute: str) -> None:
        """
        Create tables for distinct values of a filterable attribute.

        Args:
            attribute (str): The attribute name.
        """
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {attribute}_values (
                value TEXT PRIMARY KEY
            )
        """
        )

    @close
    @commit
    @connect
    def _populate_values_table(self, attribute: str) -> None:
        """
        Populate tables with distinct values for a filterable attribute.

        Args:
            attribute (str): The attribute name.
        """
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            INSERT INTO {attribute}_values (value)
            SELECT DISTINCT {attribute} FROM locations WHERE {attribute} IS NOT NULL
        """
        )

    def _validate_filter(self, filter: t.Dict[str, t.List[str]]) -> None:
        """
        Validate the filter keys and values.

        Args:
            filter (Dict[str, List[str]]): Filter to validate.

        Raises:
            ValueError: If the filter contains invalid keys or values.
        """
        valid_attributes = self._get_filter_attributes()
        invalid_keys = [k for k in filter.keys() if k not in valid_attributes]
        if invalid_keys:
            raise ValueError(
                f"Invalid filter keys: {', '.join(invalid_keys)}.\n"
                f"Valid filter keys:\n- " + "\n- ".join(sorted(valid_attributes))
            )

        for attr, values in filter.items():
            valid_values = self._get_filter_values(attr)
            valid_values_lower = {v.lower(): v for v in valid_values}

            invalid_values = [v for v in values if v not in valid_values]
            if invalid_values:
                suggestions = {
                    v: get_close_matches(v.lower(), valid_values_lower.keys(), n=1)
                    for v in invalid_values
                }
                suggestion_text = "\n- ".join(
                    (
                        f"{value}: Did you mean {valid_values_lower[matches[0]]}?"
                        if matches
                        else f"'{value}': No close matches found."
                    )
                    for value, matches in suggestions.items()
                )
                raise ValueError(
                    f"Invalid filter values for {attr}: {', '.join(invalid_values)}.\n"
                    f"Suggestions:\n- {suggestion_text}"
                )

    def _get_filter_attributes(self) -> t.List[str]:
        """
        Get the list of valid filter attributes.

        Returns:
            List[str]: List of valid filter attribute names.
        """
        location_identifier = self.config.location_identifier
        location_columns = self.config.location_columns

        filter_attributes = [
            col.name
            for col in location_columns
            if col.type == "TEXT"
            and col.name != location_identifier
            and not col.name.endswith(location_identifier)
        ]
        return filter_attributes

    def _get_filter_values(self, attribute: str) -> t.List[str]:
        """
        Get the list of valid values for a filter attribute.

        Args:
            attribute (str): The attribute name.

        Returns:
            List[str]: List of valid values.
        """
        query = f"SELECT value FROM {attribute}_values"
        result = self.execute_query(query)
        return [row[0] for row in result]

    def _construct_filter_query(
        self, filter: t.Dict[str, t.List[str]]
    ) -> t.Tuple[str, t.List[str]]:
        """
        Construct additional SQL query text and parameters for filtering.

        Args:
            filter (Dict[str, List[str]]): Filter to apply.

        Returns:
            Tuple[str, List[str]]: Additional SQL query text and parameters.
        """
        filter_key = tuple(sorted((k, tuple(v)) for k, v in (filter or {}).items()))

        if filter_key in self._filter_cache:
            return self._filter_cache[filter_key]

        self._validate_filter(filter)

        query_parts = []
        params = []
        for attr, values in filter.items():
            placeholders = ", ".join(["?"] * len(values))
            query_parts.append(f"locations.{attr} IN ({placeholders})")
            params.extend(values)
        filter_query = " AND ".join(query_parts)

        self._filter_cache[filter_key] = (filter_query, params)
        return filter_query, params

    def query_candidates(
        self,
        toponym: str,
        filter: t.Optional[t.Dict[str, t.List[str]]] = None,
    ) -> t.List[str]:
        """
        Query the database for candidate location IDs matching the toponym.

        Args:
            toponym (str): The toponym to search for.
            filter (Optional[Dict[str, List[str]]], optional): Filter to restrict candidate selection.

        Returns:
            List[str]: List of candidate location IDs.
        """
        location_identifier = self.config.location_identifier

        toponym_cleaned = re.sub(r"\"", "", toponym).strip()
        toponym_tokenized = " ".join([f'"{word}"' for word in toponym_cleaned.split()])

        params = [toponym_tokenized, toponym_cleaned]
        filter_join = ""
        filter_where = ""

        if filter:
            filter_query, filter_params = self._construct_filter_query(filter)
            filter_join = f"JOIN locations ON AdjustedScores.{location_identifier} = locations.{location_identifier}"
            filter_where = f"AND {filter_query}"
            params.extend(filter_params)

        query = f"""
            WITH ScoredMatches AS (
                SELECT {location_identifier}, name, rank AS base_score
                FROM names_fts
                WHERE names_fts MATCH ?
            ),
            AdjustedScores AS (
                SELECT {location_identifier}, name,
                    CASE
                        WHEN length(REPLACE(REPLACE(REPLACE(REPLACE(trim(name), ' ', ''), '.', ''), ',', ''), '-', '')) =
                             length(REPLACE(REPLACE(REPLACE(REPLACE(trim(?), ' ', ''), '.', ''), ',', ''), '-', '')) THEN base_score * 2
                        ELSE base_score
                    END AS score
                FROM ScoredMatches
            ),
            MinScore AS (
                SELECT MIN(score) AS MinScore FROM AdjustedScores
            )
            SELECT AdjustedScores.{location_identifier}, AdjustedScores.score
            FROM AdjustedScores
            {filter_join}
            WHERE AdjustedScores.score = (SELECT MinScore FROM MinScore)
            {filter_where}
            GROUP BY AdjustedScores.{location_identifier}
        """

        result = self.execute_query(query, tuple(params))
        return [row[0] for row in result]

    def query_locations(
        self, location_ids: t.Union[str, t.List[str]], batch_size: int = 500
    ) -> t.List[t.Optional[t.Dict[str, t.Any]]]:
        """
        Retrieve location information for a list of location IDs.

        Args:
            location_ids (Union[str, List[str]]): List of location IDs.
            batch_size (int, optional): Number of IDs per query batch. Defaults to 500.

        Returns:
            List[Optional[Dict[str, Any]]]: List of dictionaries containing location information.
        """
        location_identifier = self.config.location_identifier

        if not isinstance(location_ids, list):
            location_ids = [location_ids]

        batches = [
            location_ids[i : i + batch_size]
            for i in range(0, len(location_ids), batch_size)
        ]
        results_dict = {}

        for batch in batches:
            placeholders = ",".join("?" for _ in batch)
            query = f"""
                SELECT *
                FROM locations
                WHERE {location_identifier} IN ({placeholders})
            """
            results = self.execute_query(query, batch)

            columns = [col.name for col in self.config.location_columns]
            for row in results:
                results_dict[row[0]] = dict(zip(columns, row))

        return [results_dict.get(location_id, None) for location_id in location_ids]
