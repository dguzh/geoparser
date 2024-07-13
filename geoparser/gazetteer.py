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
        for dataset in self.config.data:
            self.download_file(dataset.url)
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

        self.create_tables(dataset)
        self.populate_tables(dataset)

    def create_tables(self, dataset: GazetteerData):
        self._create_table(dataset)
        for virtual_table in dataset.virtual_tables:
            self._create_virtual_table(virtual_table)

    @close
    @commit
    @connect
    def _create_table(self, dataset: GazetteerData):
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
    def _create_virtual_table(self, virtual_table: VirtualTable):
        cursor = self._get_cursor()
        args = ", ".join(virtual_table.args)
        kwargs = ", ".join(
            [f'{key}="{value}"' for key, value in virtual_table.kwargs.items()]
        )
        cursor.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {virtual_table.name} USING {virtual_table.using}({args}, {kwargs})"
        )

    def populate_tables(self, dataset: GazetteerData):
        self.load_file_into_table(
            os.path.join(self.data_dir, dataset.extracted_file),
            dataset.name,
            [col.name for col in dataset.columns],
            skiprows=dataset.skiprows,
        )
        for virtual_table in dataset.virtual_tables:
            self.populate_virtual_table(virtual_table, dataset.name)

    @abstractmethod
    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> list[pd.DataFrame]:
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
    @commit
    @connect
    def populate_virtual_table(self, virtual_table: VirtualTable, table_name: str):
        cursor = self._get_cursor()
        cursor.execute(
            f"INSERT INTO {virtual_table.name} (rowid, {virtual_table.args[0]}) SELECT {virtual_table.kwargs['content_rowid']}, {virtual_table.args[0]} FROM {table_name}"
        )

    @close
    @connect
    def execute_query(self, query: str, params: tuple[str, ...] = None) -> list:
        cursor = self._get_cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()
