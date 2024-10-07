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
    def query_candidates(self) -> list[int]:
        pass

    @abstractmethod
    def query_location_info(self) -> list[dict]:
        pass

    def get_location_description(
        self, location: dict[str, t.Union[int, str, float]]
    ) -> str:
        return self.format_location_description(
            location, self.location_description_template
        )

    def evaluate_conditionals(
        self,
        cond_expr: str,
    ) -> tuple[t.Optional[str], t.Optional[t.Callable[[dict], bool]]]:
        match = re.match(r"COND\[(.+?), (any|all)\{(.+?)\}\]", cond_expr)
        if not match:
            return None, None

        text, condition_type, keys = match.groups()
        keys = [key.strip("<> ") for key in keys.split(",")]

        if condition_type == "any":
            return text, lambda loc: any(loc.get(key) for key in keys)
        elif condition_type == "all":
            return text, lambda loc: all(loc.get(key) for key in keys)
        return None, None

    def substitute_conditionals(
        self, location: dict[str, t.Union[int, str, float]], template: str
    ) -> str:
        conditionals = re.findall(r"COND\[.+?\]", template)
        for cond in conditionals:
            text, conditional_func = self.evaluate_conditionals(cond)
            if conditional_func:
                replacement_text = text if conditional_func(location) else ""
                template = template.replace(cond, replacement_text, 1)
        return template

    def format_location_description(
        self, location: dict[str, t.Union[int, str, float]], template: str
    ) -> str:

        def substitute_keys(match: re.Match) -> str:
            key = match.group("key")
            value = location.get(key)
            return f"{match.group('pre')}{value}{match.group('post')}" if value else ""

        if location:
            template = self.substitute_conditionals(location, template)
            formatted_text = re.sub(
                r"(?P<pre>[^\s<>]*?)<(?P<key>\w+)>(?P<post>[^\s<>]*)",
                substitute_keys,
                template,
            )
            formatted_text = re.sub(r"\s*,\s*", ", ", formatted_text)
            formatted_text = re.sub(r",\s*$", "", formatted_text)
            formatted_text = re.sub(r"\s+", " ", formatted_text)

            return formatted_text.strip()


class LocalDBGazetteer(Gazetteer):
    data_dir = user_data_dir("geoparser", "")

    def __init__(self, db_name: str):
        super().__init__()
        self.db_path = os.path.join(LocalDBGazetteer.data_dir, db_name + ".db")
        self.config = get_gazetteer_configs()[db_name]
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

    def setup_database(self):
        print("Database setup...")

        self.clean_dir()

        os.makedirs(self.data_dir, exist_ok=True)

        self.create_names_table()

        for dataset in self.config.data:
            self.download_file(dataset.url)
            self.load_data(dataset)

        self.populate_names_fts_table()

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

    def download_file(
        self, url: str, extract_zips: bool = True, remove_zip: bool = True
    ):
        filename = url.split("/")[-1]
        file_path = os.path.join(self.data_dir, filename)
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
        if extract_zips and file_path.endswith(".zip"):
            self.extract_zip(file_path, remove=remove_zip)

    def extract_zip(self, file_path: str, remove: bool = True):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(self.data_dir)
        if remove:
            os.remove(file_path)

    def load_data(self, dataset: GazetteerData):

        self.create_table(dataset)
        self.populate_table(dataset)

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
    def create_table(self, dataset: GazetteerData):
        cursor = self._get_cursor()
        columns = ", ".join(
            [
                f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
                for col in dataset.columns
            ]
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {dataset.name} ({columns})")

    def populate_table(self, dataset: GazetteerData):
        self.load_file_into_table(
            os.path.join(self.data_dir, dataset.extracted_file),
            dataset.name,
            [col.name for col in dataset.columns],
            skiprows=dataset.skiprows,
        )

        if dataset.toponym_columns:
            self.populate_names_table(dataset)

    @close
    @commit
    @connect
    def populate_names_table(self, dataset: GazetteerData, chunksize: int = 100000):
        toponym_columns = dataset.toponym_columns
        location_identifier = self.config.location_identifier

        columns_to_select = [location_identifier] + [tc.name for tc in toponym_columns]

        query = f'SELECT {", ".join(columns_to_select)} FROM {dataset.name}'

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {dataset.name}")
        total_rows = cursor.fetchone()[0]
        total_chunks = math.ceil(total_rows / chunksize)

        chunks = pd.read_sql_query(query, self.conn, chunksize=chunksize)

        for chunk in tqdm(
            chunks, desc=f"Loading names from {dataset.name}", total=total_chunks
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
    def populate_names_fts_table(self):
        cursor = self._get_cursor()
        cursor.execute(
            f"""
            INSERT INTO names_fts (rowid, name, {self.config.location_identifier})
            SELECT id, name, {self.config.location_identifier} FROM names
        """
        )

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
    def load_file_into_table(
        self,
        file_path: str,
        table_name: str,
        columns: list[str],
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ):
        chunks = self.read_file(file_path, columns, skiprows, chunksize)
        for chunk in tqdm(
            chunks,
            desc=f"Loading {table_name}",
            total=math.ceil(sum(1 for _ in open(file_path, "rb")) / chunksize),
        ):
            chunk.to_sql(table_name, self.conn, if_exists="append", index=False)

    @close
    @connect
    def execute_query(self, query: str, params: tuple[str, ...] = None) -> list:
        cursor = self._get_cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()
