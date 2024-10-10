import math
import os
import re
import shutil
import sqlite3
import typing as t
import zipfile
from abc import ABC, abstractmethod

import pandas as pd
import requests
from appdirs import user_data_dir
from tqdm.auto import tqdm

from geoparser.config import get_gazetteer_configs
from geoparser.config.models import GazetteerData


class Gazetteer(ABC):

    @abstractmethod
    def create_location_description(self, location: dict[str, str]) -> str:
        pass

    def get_location_description(
        self, location: dict[str, t.Union[int, str, float]]
    ) -> str:
        return self.create_location_description(location)


class LocalDBGazetteer(Gazetteer):

    def __init__(self, gazetteer_name: str):
        super().__init__()
        self.data_dir = os.path.join(user_data_dir("geoparser", ""), gazetteer_name)
        self.db_path = os.path.join(self.data_dir, gazetteer_name + ".db")
        self.config = get_gazetteer_configs()[gazetteer_name]
        self.conn = None

    def connect(func):
        def call(self, *args, **kwargs):
            self._initiate_connection()
            ret = func(self, *args, **kwargs)
            return ret

        return call

    def commit(func):
        def call(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self._commit()
            return ret

        return call

    def close(func):
        def call(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self._close_connection()
            return ret

        return call

    def _initiate_connection(self):
        self.conn = sqlite3.connect(self.db_path)

    def _close_connection(self):
        self.conn.close()

    def _commit(self):
        self.conn.commit()

    def _get_cursor(self) -> sqlite3.Cursor:
        return self.conn.cursor()

    @close
    @connect
    def execute_query(self, query: str, params: tuple[str, ...] = None) -> list:
        cursor = self._get_cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()

    def setup_database(self):
        print("Database setup...")

        self.clean_dir()

        os.makedirs(self.data_dir, exist_ok=True)

        for dataset in self.config.data:
            self.download_file(dataset)
            self.load_data(dataset)

        self.create_names_table()
        self.populate_names_table()

        self.create_names_fts_table()
        self.populate_names_fts_table()

        self.create_locations_table()
        self.populate_locations_table()

        self.drop_redundant_tables()

        self.clean_dir(keep_db=True)

        print("Database setup complete.")

    def clean_dir(self, keep_db: bool = False):

        if os.path.exists(self.data_dir):
            for file_name in os.listdir(self.data_dir):
                if keep_db and (
                    file_name.endswith(".db") or file_name.endswith(".db-journal")
                ):
                    continue
                else:
                    try:
                        os.remove(os.path.join(self.data_dir, file_name))
                    except IsADirectoryError:
                        os.rmdir(os.path.join(self.data_dir, file_name))
                    except PermissionError:
                        shutil.rmtree(os.path.join(self.data_dir, file_name))

    @close
    @commit
    @connect
    def drop_redundant_tables(self):
        cursor = self._get_cursor()
        tables_to_drop = [dataset.name for dataset in self.config.data]
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
        cursor.execute("VACUUM;")

    def download_file(self, dataset: GazetteerData):
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
            self.extract_zip(file_path, dataset.extracted_files)

    def extract_zip(self, file_path: str, extracted_files: t.List[str]):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            for file_name in extracted_files:
                zip_ref.extract(file_name, self.data_dir)

    def load_data(self, dataset: GazetteerData):
        self.create_data_table(dataset)
        self.populate_data_table(dataset)

    @abstractmethod
    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
        pass

    @close
    @commit
    @connect
    def create_data_table(self, dataset: GazetteerData):
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
    def populate_data_table(self, dataset: GazetteerData):
        file_path = os.path.join(self.data_dir, dataset.extracted_files[0])
        table_name = dataset.name
        columns = [col.name for col in dataset.columns]
        skiprows = dataset.skiprows
        chunksize = 100000

        chunks, n_chunks = self.read_file(file_path, columns, skiprows, chunksize)

        for chunk in tqdm(
            chunks,
            desc=f"Loading {table_name}",
            total=n_chunks,
        ):
            chunk.to_sql(table_name, self.conn, if_exists="append", index=False)

    @close
    @commit
    @connect
    def create_names_table(self):
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {self.config.location_identifier} INTEGER,
                name TEXT
            )
        """
        )

    @close
    @commit
    @connect
    def populate_names_table(self, chunksize: int = 100000):
        for dataset in self.config.data:
            if dataset.toponym_columns:

                toponym_columns = dataset.toponym_columns
                location_identifier = self.config.location_identifier

                columns_to_select = [location_identifier] + [
                    tc.name for tc in toponym_columns
                ]

                query = f'SELECT {", ".join(columns_to_select)} FROM {dataset.name}'

                cursor = self.conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {dataset.name}")
                total_rows = cursor.fetchone()[0]
                total_chunks = math.ceil(total_rows / chunksize)

                chunks = pd.read_sql_query(query, self.conn, chunksize=chunksize)

                for chunk in tqdm(
                    chunks,
                    desc=f"Loading names from {dataset.name}",
                    total=total_chunks,
                ):
                    chunk[location_identifier] = chunk[location_identifier].astype(str)

                    name_dfs = []

                    for tc in toponym_columns:
                        name = tc.name
                        if name not in chunk.columns:
                            continue

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
                            self.conn,
                            if_exists="append",
                            index=False,
                            method="multi",
                            chunksize=400,
                        )

    @close
    @commit
    @connect
    def create_names_fts_table(self):
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
    def populate_names_fts_table(self):
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
    def create_locations_table(self):
        columns = self.config.location_columns
        cursor = self._get_cursor()
        columns_def = ", ".join(
            f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
            for col in columns
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS locations ({columns_def})")

    @abstractmethod
    def populate_locations_table(self):
        pass

    def query_candidates(
        self,
        toponym: str,
    ) -> list[int]:

        location_identifier = self.config.location_identifier

        toponym = re.sub(r"\"", "", toponym).strip()
        toponym = " ".join([f'"{word}"' for word in toponym.split()])

        query = f"""
            WITH RankedMatches AS (
                SELECT
                    names_fts.{location_identifier},
                    bm25(names_fts) AS rank
                FROM names_fts
                WHERE names_fts MATCH ?
            ),
            MinRank AS (
                SELECT MIN(rank) AS MinRank FROM RankedMatches
            )
            SELECT {location_identifier}
            FROM RankedMatches
            WHERE RankedMatches.rank = (SELECT MinRank FROM MinRank)
            GROUP BY {location_identifier}
        """

        result = self.execute_query(query, (toponym,))
        return [row[0] for row in result]

    def query_location_info(
        self, location_ids: list[int], batch_size: int = 500
    ) -> list[dict]:
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
