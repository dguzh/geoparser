import re
import sqlite3
import pandas as pd
from appdirs import user_data_dir
import os
from tqdm.auto import tqdm

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
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
    )''')

    cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS allCountries_fts USING fts5(
        name,
        content='allCountries',
        content_rowid='geonameid',
        tokenize="unicode61 tokenchars '.'"
    )''')

    cursor.execute('''
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
    )''')

    cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS alternateNames_fts USING fts5(
        alternate_name,
        content='alternateNames',
        content_rowid='alternateNameId',
        tokenize="unicode61 tokenchars '.'"
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin1CodesASCII (
        admin1_full_code TEXT PRIMARY KEY,
        admin1_name TEXT,
        admin1_asciiname TEXT,
        admin1_geonameid INTEGER
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin2Codes (
        admin2_full_code TEXT PRIMARY KEY,
        admin2_name TEXT,
        admin2_asciiname TEXT,
        admin2_geonameid INTEGER
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS countryInfo (
        ISO TEXT,
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
        country_geonameid INTEGER PRIMARY KEY,
        neighbours TEXT,
        equivalentFipsCode TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS featureCodes (
        feature_full_code TEXT PRIMARY KEY,
        feature_name TEXT,
        feature_description TEXT
    )''')

    conn.commit()
    conn.close()

def load_data_into_database(db_path, data_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load allCountries.txt
    chunks = pd.read_csv(os.path.join(data_dir, 'allCountries.txt'), delimiter='\t', header=None, names=[
        'geonameid', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude', 'feature_class', 'feature_code',
        'country_code', 'cc2', 'admin1_code', 'admin2_code', 'admin3_code', 'admin4_code', 'population', 'elevation',
        'dem', 'timezone', 'modification_date'], chunksize=500000, dtype=str)

    for chunk in tqdm(chunks, desc="Loading allCountries"):
        chunk.to_sql('allCountries', conn, if_exists='append', index=False)

    # Populate the FTS table
    cursor.execute('''
    INSERT INTO allCountries_fts (rowid, name)
    SELECT geonameid, name FROM allCountries
    ''')
    conn.commit()

    # Load alternateNames.txt
    chunks = pd.read_csv(os.path.join(data_dir, 'alternateNames.txt'), delimiter='\t', header=None, names=[
        'alternateNameId', 'geonameid', 'isolanguage', 'alternate_name', 'isPreferredName', 
        'isShortName', 'isColloquial', 'isHistoric', 'fromPeriod', 'toPeriod'], chunksize=500000, dtype=str)

    for chunk in tqdm(chunks, desc="Loading alternateNames"):
        chunk.to_sql('alternateNames', conn, if_exists='append', index=False)

    # Populate the FTS table for alternate names
    cursor.execute('''
    INSERT INTO alternateNames_fts (rowid, alternate_name)
    SELECT alternateNameId, alternate_name FROM alternateNames
    ''')
    conn.commit()

    # Load other data files
    pd.read_csv(os.path.join(data_dir, 'admin1CodesASCII.txt'), delimiter='\t', header=None, names=[
        'admin1_full_code', 'admin1_name', 'admin1_asciiname', 'admin1_geonameid']).to_sql('admin1CodesASCII', conn, if_exists='append', index=False)

    pd.read_csv(os.path.join(data_dir, 'admin2Codes.txt'), delimiter='\t', header=None, names=[
        'admin2_full_code', 'admin2_name', 'admin2_asciiname', 'admin2_geonameid']).to_sql('admin2Codes', conn, if_exists='append', index=False)

    pd.read_csv(os.path.join(data_dir, 'countryInfo.txt'), delimiter='\t', header=None, skiprows=50, names=[
        'ISO', 'ISO3', 'ISO_Numeric', 'fips', 'country_name', 'capital', 'area', 'country_population', 'continent', 'tld', 'currencyCode',
        'currencyName', 'Phone', 'postalCodeFormat', 'postalCodeRegex', 'languages', 'country_geonameid', 'neighbours', 'equivalentFipsCode']).to_sql('countryInfo', conn, if_exists='append', index=False)
    
    pd.read_csv(os.path.join(data_dir, 'featureCodes_en.txt'), delimiter='\t', header=None, names=[
        'feature_full_code', 'feature_name', 'feature_description']).to_sql('featureCodes', conn, if_exists='append', index=False)

    conn.close()

def main():
    data_dir = user_data_dir('geoparser')
    db_path = os.path.join(data_dir, 'geonames.db')
    
    print("Building GeoNames database...")
    create_database(db_path)
    load_data_into_database(db_path, data_dir)

if __name__ == "__main__":
    main()
