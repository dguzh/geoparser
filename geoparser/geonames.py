import re
import typing as t

import pandas as pd

from geoparser.gazetteer import LocalDBGazetteer


class GeoNames(LocalDBGazetteer):
    def __init__(self):
        super().__init__("geonames")
        self.location_description_template = "<name> (<feature_name>) COND[in, any{<admin2_name>, <admin1_name>, <country_name>}] <admin2_name>, <admin1_name>, <country_name>"

    def read_file(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
        return self.read_tsv(file_path, columns, skiprows, chunksize)

    def read_tsv(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> t.Iterator[pd.DataFrame]:
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
        return (chunk for chunk in chunks)

    @LocalDBGazetteer.close
    @LocalDBGazetteer.commit
    @LocalDBGazetteer.connect
    def populate_locations_table(self):
        cursor = self._get_cursor()

        insert_query = """
            INSERT INTO locations (
                geonameid, name, feature_type, latitude, longitude, elevation, population,
                admin2_geonameid, admin1_geonameid, country_geonameid
            )
            SELECT
                ac.geonameid,
                ac.name,
                fc.feature_name AS feature_type,
                ac.latitude,
                ac.longitude,
                ac.elevation,
                ac.population,
                a2.admin2_geonameid,
                a1.admin1_geonameid,
                ci.country_geonameid
            FROM
                allCountries ac
            LEFT JOIN featureCodes fc ON ac.feature_class || '.' || ac.feature_code = fc.feature_full_code
            LEFT JOIN countryInfo ci ON ac.country_code = ci.ISO
            LEFT JOIN admin1CodesASCII a1 ON ci.ISO || '.' || ac.admin1_code = a1.admin1_full_code
            LEFT JOIN admin2Codes a2 ON ci.ISO || '.' || ac.admin1_code || '.' || ac.admin2_code = a2.admin2_full_code
        """
        cursor.execute(insert_query)
