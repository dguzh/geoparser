import pkg_resources
import pandas as pd
import numpy as np

class Gazetteer:
    def __init__(self):
        self.geonames_file = pkg_resources.resource_filename('geoparser', 'geonames/allCountries.txt')
        self.admin1_file = pkg_resources.resource_filename('geoparser', 'geonames/admin1CodesASCII.txt')
        self.admin2_file = pkg_resources.resource_filename('geoparser', 'geonames/admin2Codes.txt')
        self.country_info_file = pkg_resources.resource_filename('geoparser', 'geonames/countryInfo.txt')
        self.feature_codes_file = pkg_resources.resource_filename('geoparser', 'geonames/featureCodes_en.txt')
        self.data = None

    def load(self, all_candidates):
        
        cols = ['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude', 
                 'feature_class', 'feature_code', 'country_code', 'cc2', 'admin1_code', 'admin2_code', 
                 'admin3_code', 'admin4_code', 'population', 'elevation', 'dem', 'timezone', 
                 'modification_date']

        cols_to_load = ['geonameid', 'name', 'latitude', 'longitude', 'feature_code',
                        'country_code', 'admin1_code', 'admin2_code', 'population', 'elevation']

        dtype = {
            'geonameid': 'Int64',
            'feature_code': str,
            'country_code': str,
            'admin1_code': str,
            'admin2_code': str
        }

        chunks = pd.read_csv(self.geonames_file, delimiter='\t', header=None,
                             names=cols, usecols=cols_to_load, low_memory=False, chunksize=500000,
                             dtype=dtype)

        filtered_chunks = []
        for chunk in chunks:
            filtered_chunk = chunk[chunk['geonameid'].isin(all_candidates)]
            if not filtered_chunk.empty:
                filtered_chunks.append(filtered_chunk)
        
        if filtered_chunks:
            self.data = pd.concat(filtered_chunks)
            self.data.reset_index(drop=True, inplace=True)
            self.enrich_data()

    def enrich_data(self):
        country_df = self.load_country_data(self.country_info_file)
        admin1_df = self.load_admin1_data(self.admin1_file)
        admin2_df = self.load_admin2_data(self.admin2_file)
        feature_df = self.load_feature_data(self.feature_codes_file)

        self.merge_data(country_df, admin1_df, admin2_df, feature_df)

        self.data['country_name'] = self.data.apply(lambda x: np.nan if pd.isna(x['country_code']) else x['country_name'], axis=1)

        self.data['pseudotext'] = self.data.apply(self.pseudotext_generator, axis=1)

    def load_country_data(self, country_info_file):
        cols = ['country_code', 'ISO3', 'ISO-Numeric', 'fips', 'country_name', 'Capital', 'Area(in sq km)',
                'Population', 'Continent', 'tld', 'CurrencyCode', 'CurrencyName', 'Phone', 'Postal Code Format',
                'Postal Code Regex', 'Languages', 'country_geonameid', 'neighbours', 'EquivalentFipsCode']
        dtype = {'country_geonameid': 'Int64'}
        country_df = pd.read_csv(country_info_file, sep='\t', header=None, skiprows=50, names=cols, dtype=dtype)
        return country_df[['country_code', 'country_name', 'country_geonameid']]

    def load_admin1_data(self, admin1_file):
        cols = ['admin1_full_code', 'admin1_name', 'ascii_name', 'admin1_geonameid']
        dtype = {'admin1_geonameid': 'Int64'}
        admin1_df = pd.read_csv(admin1_file, sep='\t', header=None, names=cols, dtype=dtype)
        admin1_df[['country_code', 'admin1_code']] = admin1_df['admin1_full_code'].str.split('.', expand=True).astype(str)
        return admin1_df[['country_code', 'admin1_code', 'admin1_name', 'admin1_geonameid']]

    def load_admin2_data(self, admin2_file):
        cols = ['admin2_full_code', 'admin2_name', 'ascii_name', 'admin2_geonameid']
        dtype = {'admin2_geonameid': 'Int64'}
        admin2_df = pd.read_csv(admin2_file, sep='\t', header=None, names=cols, dtype=dtype)
        admin2_df[['country_code', 'admin1_code', 'admin2_code']] = admin2_df['admin2_full_code'].str.split('.', expand=True).astype(str)
        return admin2_df[['country_code', 'admin1_code', 'admin2_code', 'admin2_name', 'admin2_geonameid']]

    def load_feature_data(self, feature_codes_file):
        cols = ['feature_full_code', 'feature_name', 'feature_description']
        feature_df = pd.read_csv(feature_codes_file, sep='\t', header=None, names=cols)
        feature_df[['feature_class', 'feature_code']] = feature_df['feature_full_code'].str.split('.', expand=True).astype(str)
        return feature_df[['feature_code', 'feature_name']]

    def merge_data(self, country_df, admin1_df, admin2_df, feature_df):
        self.data = self.data.merge(country_df, on='country_code', how='left')
        self.data = self.data.merge(admin1_df, on=['country_code', 'admin1_code'], how='left')
        self.data = self.data.merge(admin2_df, on=['country_code', 'admin1_code', 'admin2_code'], how='left')
        self.data = self.data.merge(feature_df, on='feature_code', how='left')

    def pseudotext_generator(self, row):
        components = [row['name']]
        for field in ['admin2_name', 'admin1_name', 'country_name']:
            if pd.notna(row[field]):
                components.append(row[field])
        location_str = " in " + ", ".join(components[1:]) if len(components) > 1 else ""
        feature_str = f" ({row['feature_name']})" if pd.notna(row['feature_name']) else ""
    
        return f"{components[0]}{feature_str}{location_str}"