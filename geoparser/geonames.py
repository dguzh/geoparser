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

from geoparser.gazetteer import Gazetteer


class GeoNames(Gazetteer):
    def __init__(self):
        super().__init__("geonames")
        self.location_description_template = "<name> (<feature_name>) COND[in, any{<admin2_name>, <admin1_name>, <country_name>}] <admin2_name>, <admin1_name>, <country_name>"

    def setup_database(self):
        print("Database setup...")

        self.clean_dir()

        self.download_data()
        self.load_data()

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

    def download_data(self):
        urls = [
            "https://download.geonames.org/export/dump/allCountries.zip",
            "https://download.geonames.org/export/dump/alternateNames.zip",
            "https://download.geonames.org/export/dump/admin1CodesASCII.txt",
            "https://download.geonames.org/export/dump/admin2Codes.txt",
            "https://download.geonames.org/export/dump/countryInfo.txt",
            "https://download.geonames.org/export/dump/featureCodes_en.txt",
        ]
        os.makedirs(self.data_dir, exist_ok=True)
        for url in urls:
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

    def load_data(self):

        conn = sqlite3.connect(self.db_path)

        self.create_tables(conn)
        self.populate_tables(conn)

        conn.close()

    def create_tables(self, conn: sqlite3.Connection):

        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS allCountries (
            geonameid INTEGER PRIMARY KEY,
            name TEXT,
            asciiname TEXT,
            alternatenames TEXT,
            latitude REAL,
            longitude REAL,
            feature_class TEXT,
            feature_code TEXT,
            country_code TEXT,
            cc2 TEXT,
            admin1_code TEXT,
            admin2_code TEXT,
            admin3_code TEXT,
            admin4_code TEXT,
            population INTEGER,
            elevation INTEGER,
            dem INTEGER,
            timezone TEXT,
            modification_date TEXT
        )"""
        )

        cursor.execute(
            """
        CREATE VIRTUAL TABLE IF NOT EXISTS allCountries_fts USING fts5(
            name,
            content='allCountries',
            content_rowid='geonameid',
            tokenize="unicode61 tokenchars '.'"
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS alternateNames (
            alternateNameId INTEGER PRIMARY KEY,
            geonameid INTEGER,
            isolanguage TEXT,
            alternate_name TEXT,
            isPreferredName BOOLEAN,
            isShortName BOOLEAN,
            isColloquial BOOLEAN,
            isHistoric BOOLEAN,
            fromPeriod TEXT,
            toPeriod TEXT
        )"""
        )

        cursor.execute(
            """
        CREATE VIRTUAL TABLE IF NOT EXISTS alternateNames_fts USING fts5(
            alternate_name,
            content='alternateNames',
            content_rowid='alternateNameId',
            tokenize="unicode61 tokenchars '.'"
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS admin1CodesASCII (
            admin1_full_code TEXT PRIMARY KEY,
            admin1_name TEXT,
            admin1_asciiname TEXT,
            admin1_geonameid INTEGER
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS admin2Codes (
            admin2_full_code TEXT PRIMARY KEY,
            admin2_name TEXT,
            admin2_asciiname TEXT,
            admin2_geonameid INTEGER
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS countryInfo (
            ISO TEXT PRIMARY KEY,
            ISO3 TEXT,
            ISO_Numeric INTEGER,
            fips TEXT,
            country_name TEXT,
            capital TEXT,
            area REAL,
            country_population INTEGER,
            continent TEXT,
            tld TEXT,
            currencyCode TEXT,
            currencyName TEXT,
            Phone TEXT,
            postalCodeFormat TEXT,
            postalCodeRegex TEXT,
            languages TEXT,
            country_geonameid INTEGER,
            neighbours TEXT,
            equivalentFipsCode TEXT
        )"""
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS featureCodes (
            feature_full_code TEXT PRIMARY KEY,
            feature_name TEXT,
            feature_description TEXT
        )"""
        )

        conn.commit()

    def populate_tables(self, conn: sqlite3.Connection):

        cursor = conn.cursor()

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "allCountries.txt"),
            "allCountries",
            [
                "geonameid",
                "name",
                "asciiname",
                "alternatenames",
                "latitude",
                "longitude",
                "feature_class",
                "feature_code",
                "country_code",
                "cc2",
                "admin1_code",
                "admin2_code",
                "admin3_code",
                "admin4_code",
                "population",
                "elevation",
                "dem",
                "timezone",
                "modification_date",
            ],
        )

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "alternateNames.txt"),
            "alternateNames",
            [
                "alternateNameId",
                "geonameid",
                "isolanguage",
                "alternate_name",
                "isPreferredName",
                "isShortName",
                "isColloquial",
                "isHistoric",
                "fromPeriod",
                "toPeriod",
            ],
        )

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "admin1CodesASCII.txt"),
            "admin1CodesASCII",
            ["admin1_full_code", "admin1_name", "admin1_asciiname", "admin1_geonameid"],
        )

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "admin2Codes.txt"),
            "admin2Codes",
            ["admin2_full_code", "admin2_name", "admin2_asciiname", "admin2_geonameid"],
        )

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "countryInfo.txt"),
            "countryInfo",
            [
                "ISO",
                "ISO3",
                "ISO_Numeric",
                "fips",
                "country_name",
                "capital",
                "area",
                "country_population",
                "continent",
                "tld",
                "currencyCode",
                "currencyName",
                "Phone",
                "postalCodeFormat",
                "postalCodeRegex",
                "languages",
                "country_geonameid",
                "neighbours",
                "equivalentFipsCode",
            ],
            skiprows=50,
        )

        self.load_file_into_table(
            conn,
            os.path.join(self.data_dir, "featureCodes_en.txt"),
            "featureCodes",
            ["feature_full_code", "feature_name", "feature_description"],
        )

        cursor.execute(
            """
        INSERT INTO allCountries_fts (rowid, name)
        SELECT geonameid, name FROM allCountries
        """
        )

        cursor.execute(
            """
        INSERT INTO alternateNames_fts (rowid, alternate_name)
        SELECT alternateNameId, alternate_name FROM alternateNames
        """
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

        os.remove(file_path)

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
