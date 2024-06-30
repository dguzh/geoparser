import math
import os
import re
import shutil
import sqlite3
import typing as t
import zipfile

import pandas as pd
import requests
from tqdm.auto import tqdm

from geoparser.config import get_gazetteer_configs
from geoparser.config.models import GazetteerData
from geoparser.gazetteer import Gazetteer


class GeoNames(Gazetteer):
    def __init__(self):
        super().__init__("geonames")
        self.config = get_gazetteer_configs()["geonames"]
        self.location_description_template = "<name> (<feature_name>) COND[in, any{<admin2_name>, <admin1_name>, <country_name>}] <admin2_name>, <admin1_name>, <country_name>"

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

    def download_file(self, url: str):
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
        if file_path.endswith(".zip"):
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(self.data_dir)
            os.remove(file_path)

    def load_data(self, dataset: GazetteerData):

        conn = sqlite3.connect(self.db_path)

        self.create_tables(conn, dataset)
        self.populate_tables(conn, dataset)

        conn.close()

    def create_tables(self, conn: sqlite3.Connection, dataset: GazetteerData):

        cursor = conn.cursor()

        columns = ", ".join(
            [
                f"{col.name} {col.type}{' PRIMARY KEY' if col.primary else ''}"
                for col in dataset.columns
            ]
        )
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {dataset.name} ({columns})")

        for virtual_table in dataset.virtual_tables:
            args = ", ".join(virtual_table.args)
            kwargs = ", ".join(
                [f'{key}="{value}"' for key, value in virtual_table.kwargs.items()]
            )
            cursor.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {virtual_table.name} USING {virtual_table.using}({args}, {kwargs})"
            )

        conn.commit()

    def populate_tables(self, conn: sqlite3.Connection, dataset: GazetteerData):

        cursor = conn.cursor()
        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, f"{dataset.name}.txt"),
            dataset.name,
            [col.name for col in dataset.columns],
            skiprows=dataset.skiprows,
        )

        for virtual_table in dataset.virtual_tables:
            cursor.execute(
                f"INSERT INTO {virtual_table.name} (rowid, {virtual_table.args[0]}) SELECT {virtual_table.kwargs['content_rowid']}, {virtual_table.args[0]} FROM {dataset.name}"
            )

        conn.commit()

    def load_file_into_table(
        self,
        conn: sqlite3.Connection,
        file_path: str,
        table_name: str,
        columns: list[str],
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ):

        chunks = pd.read_csv(
            file_path,
            delimiter="\t",
            header=None,
            names=columns,
            chunksize=chunksize,
            dtype=str,
            skiprows=skiprows,
        )

        for chunk in tqdm(
            chunks,
            desc=f"Loading {table_name}",
            total=math.ceil(sum(1 for row in open(file_path, "rb")) / chunksize),
        ):
            chunk.to_sql(table_name, conn, if_exists="append", index=False)

    def query_candidates(
        self,
        toponym: str,
        country_filter: list[str] = None,
        feature_filter: list[str] = None,
    ) -> list[int]:

        toponym = re.sub(r"\"", "", toponym).strip()

        toponym = " ".join([f'"{word}"' for word in toponym.split()])

        base_query = """
            WITH MinRankAllCountries AS (
                SELECT MIN(rank) AS MinRank FROM allCountries_fts WHERE allCountries_fts MATCH ?
            ),
            MinRankAlternateNames AS (
                SELECT MIN(rank) AS MinRank FROM alternateNames_fts WHERE alternateNames_fts MATCH ?
            ),
            CombinedResults AS (
                SELECT allCountries_fts.rowid as geonameid, allCountries_fts.rank as rank
                FROM allCountries_fts
                WHERE allCountries_fts MATCH ?

                UNION

                SELECT alternateNames.geonameid, alternateNames_fts.rank as rank
                FROM alternateNames_fts
                JOIN alternateNames ON alternateNames_fts.rowid = alternateNames.alternateNameId
                WHERE alternateNames_fts MATCH ?
            )
            SELECT ac.geonameid
            FROM CombinedResults cr
            JOIN allCountries ac ON cr.geonameid = ac.geonameid
            WHERE (cr.rank = (SELECT MinRank FROM MinRankAllCountries)
                   OR cr.rank = (SELECT MinRank FROM MinRankAlternateNames))
        """

        where_clauses = []
        params = [toponym, toponym, toponym, toponym]

        # Adding filters for country codes
        if country_filter:
            where_clauses.append(
                f"ac.country_code IN ({','.join(['?' for _ in country_filter])})"
            )
            params.extend(country_filter)

        # Adding filters for feature classes
        if feature_filter:
            where_clauses.append(
                f"ac.feature_class IN ({','.join(['?' for _ in feature_filter])})"
            )
            params.extend(feature_filter)

        # Append additional filters if present
        if where_clauses:
            base_query += f" AND {' AND '.join(where_clauses)}"

        base_query += " GROUP BY ac.geonameid ORDER BY cr.rank"

        # Execute query with the constructed parameters
        result = self.execute_query(base_query, tuple(params))
        return [row[0] for row in result]

    def query_location_info(
        self, location_ids: list[int], batch_size: int = 500
    ) -> list[dict]:

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
            SELECT geonameid, name, admin2_geonameid, admin2_name, admin1_geonameid, admin1_name, country_geonameid, country_name, feature_name, latitude, longitude, elevation, population
            FROM allCountries
            LEFT JOIN countryInfo ON allCountries.country_code = countryInfo.ISO
            LEFT JOIN admin1CodesASCII ON countryInfo.ISO || '.' || allCountries.admin1_code = admin1CodesASCII.admin1_full_code
            LEFT JOIN admin2Codes ON countryInfo.ISO || '.' || allCountries.admin1_code || '.' || allCountries.admin2_code = admin2Codes.admin2_full_code
            LEFT JOIN featureCodes ON allCountries.feature_class || '.' || allCountries.feature_code = featureCodes.feature_full_code
            WHERE geonameid IN ({placeholders})
            """

            results = self.execute_query(query, batch)

            results_dict.update(
                {
                    row[0]: {
                        "geonameid": row[0],
                        "name": row[1],
                        "admin2_geonameid": row[2],
                        "admin2_name": row[3],
                        "admin1_geonameid": row[4],
                        "admin1_name": row[5],
                        "country_geonameid": row[6],
                        "country_name": row[7],
                        "feature_name": row[8],
                        "latitude": row[9],
                        "longitude": row[10],
                        "elevation": row[11],
                        "population": row[12],
                    }
                    for row in results
                }
            )

        return [results_dict.get(location_id, None) for location_id in location_ids]
