import math
import re
import typing as t

import pandas as pd

from geoparser.gazetteers.gazetteer import LocalDBGazetteer


class GeoNames(LocalDBGazetteer):
    def __init__(self):
        super().__init__("geonames")

    def create_location_description(self, location: dict[str, str]) -> str:
        name = location["name"] or ""
        feature = f' ({location["feature_type"]})' if location["feature_type"] else ""

        in_condition = any(
            [
                location.get("admin2_name")
                and location.get("feature_type")
                not in [
                    "second-order administrative division",
                    "first-order administrative division",
                    "independent political entity",
                ],
                location.get("admin1_name")
                and location.get("feature_type")
                not in [
                    "first-order administrative division",
                    "independent political entity",
                ],
                location.get("country_name")
                and location.get("feature_type")
                not in [
                    "independent political entity",
                ],
            ]
        )
        in_text = " in" if in_condition else ""

        admin2 = (
            f' {location.get("admin2_name")},'
            if location.get("admin2_name")
            and location.get("feature_type")
            not in [
                "second-order administrative division",
                "first-order administrative division",
                "independent political entity",
            ]
            else ""
        )

        admin1 = (
            f' {location.get("admin1_name")},'
            if location.get("admin1_name")
            and location.get("feature_type")
            not in [
                "first-order administrative division",
                "independent political entity",
            ]
            else ""
        )

        country = (
            f' {location.get("country_name")}'
            if location.get("country_name")
            and location.get("feature_type")
            not in [
                "independent political entity",
            ]
            else ""
        )

        return f"{name}{feature}{in_text}{admin2}{admin1}{country}".strip(" ,")

    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Tuple[t.Iterator[pd.DataFrame], int]:

        total_lines = sum(1 for _ in open(file_path, "rb"))
        n_chunks = math.ceil(total_lines / chunksize)

        chunks = pd.read_csv(
            file_path,
            delimiter="\t",
            header=None,
            names=columns,
            chunksize=chunksize,
            dtype=str,
            skiprows=skiprows,
        )
        if not chunksize:
            chunks = [chunks]

        return (chunk for chunk in chunks), n_chunks

    @LocalDBGazetteer.close
    @LocalDBGazetteer.commit
    @LocalDBGazetteer.connect
    def populate_locations_table(self):
        cursor = self._get_cursor()

        insert_query = """
            INSERT INTO locations (
                geonameid, name, feature_type, latitude, longitude, elevation, population,
                admin2_geonameid, admin2_name, admin1_geonameid, admin1_name, country_geonameid, country_name
            )
            SELECT
                ac.geonameid,
                ac.name,
                fc.name AS feature_type,
                ac.latitude,
                ac.longitude,
                ac.elevation,
                ac.population,
                a2.geonameid AS admin2_geonameid,
                a2.name AS admin2_name,
                a1.geonameid AS admin1_geonameid,
                a1.name AS admin1_name,
                ci.geonameid AS country_geonameid,
                ci.Country AS country_name
            FROM
                allCountries ac
            LEFT JOIN featureCodes fc ON ac.feature_class || '.' || ac.feature_code = fc.code
            LEFT JOIN countryInfo ci ON ac.country_code = ci.ISO
            LEFT JOIN admin1CodesASCII a1 ON ci.ISO || '.' || ac.admin1_code = a1.code
            LEFT JOIN admin2Codes a2 ON ci.ISO || '.' || ac.admin1_code || '.' || ac.admin2_code = a2.code
        """
        cursor.execute(insert_query)
