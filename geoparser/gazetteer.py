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
from geoparser.config.models import GazetteerData, VirtualTable


class Gazetteer(ABC):
    def __init__(self, db_name: str):
        self.data_dir = user_data_dir("geoparser", "")
        self.db_path = os.path.join(self.data_dir, db_name + ".db")

    @abstractmethod
    def query_candidates(self):
        pass

    @abstractmethod
    def query_location_info(self):
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
    def __init__(self, db_name: str):
        super().__init__(db_name)
        self.config = get_gazetteer_configs()[db_name]

    def setup_database(self):
        print("Database setup...")

        self.clean_dir()

        for dataset in self.config.data:
            self.download_data(dataset.url)
            self.load_data(dataset)

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

    def download_data(self, url: str):
        os.makedirs(self.data_dir, exist_ok=True)
        self.download_file(url)

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

        conn = sqlite3.connect(self.db_path)

        self.create_tables(conn, dataset)
        self.populate_tables(conn, dataset)

        conn.close()

    def create_tables(self, conn: sqlite3.Connection, dataset: GazetteerData):
        self._create_table(conn, dataset)
        for virtual_table in dataset.virtual_tables:
            self._create_virtual_table(conn, virtual_table)

    def _create_table(self, conn: sqlite3.Connection, dataset: GazetteerData):
        cursor = conn.cursor()
        columns = ", ".join(
            [
                f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
                for col in dataset.columns
            ]
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {dataset.name} ({columns})")
        conn.commit()

    def _create_virtual_table(
        self, conn: sqlite3.Connection, virtual_table: VirtualTable
    ):
        cursor = conn.cursor()
        args = ", ".join(virtual_table.args)
        kwargs = ", ".join(
            [f'{key}="{value}"' for key, value in virtual_table.kwargs.items()]
        )
        cursor.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {virtual_table.name} USING {virtual_table.using}({args}, {kwargs})"
        )
        conn.commit()

    def populate_tables(self, conn: sqlite3.Connection, dataset: GazetteerData):
        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, dataset.extracted_file),
            dataset.name,
            [col.name for col in dataset.columns],
            skiprows=dataset.skiprows,
        )
        conn.commit()
        for virtual_table in dataset.virtual_tables:
            self.populate_virtual_table(conn, virtual_table, virtual_table)

    @abstractmethod
    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> list[pd.DataFrame]:
        pass

    def load_file_into_table(
        self,
        conn: sqlite3.Connection,
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
            total=math.ceil(sum(1 for row in open(file_path, "rb")) / chunksize),
        ):
            chunk.to_sql(table_name, conn, if_exists="append", index=False)

    def populate_virtual_table(
        self, conn: sqlite3.Connection, virtual_table: VirtualTable, table_name: str
    ):
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO {virtual_table.name} (rowid, {virtual_table.args[0]}) SELECT {virtual_table.kwargs['content_rowid']}, {virtual_table.args[0]} FROM {table_name}"
        )
        conn.commit()

    def execute_query(self, query: str, params: tuple[str, ...] = None) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
