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
    ) -> list[pd.DataFrame]:
        return self.read_tsv(file_path, columns, skiprows, chunksize)

    def read_tsv(
        self,
        file_path: str,
        columns: list[str] = None,
        skiprows: t.Union[int, list[int], t.Callable] = None,
        chunksize: int = 100000,
    ) -> list[pd.DataFrame]:
        chunks = pd.read_csv(
            file_path,
            delimiter="\t",
            header=None,
            names=columns,
            chunksize=chunksize,
            dtype=str,
            skiprows=skiprows,
        )
        return chunks

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
