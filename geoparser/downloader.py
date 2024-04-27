import os
import re
import sys
import requests
import pickle
import unicodedata
from requests.exceptions import HTTPError
import zipfile
import subprocess
import spacy
from tqdm.auto import tqdm
from appdirs import user_data_dir

def download_spacy_models():
    models = ["en_core_web_sm", "en_core_web_trf"]
    for model in models:
        if not spacy.util.is_package(model):
            try:
                subprocess.check_call([sys.executable, "-m", "spacy", "download", model])
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while downloading spaCy model '{model}': {e}")
                sys.exit(1)
        else:
            print(f"Model '{model}' already exists.")

def download_file(url, data_dir):
    filename = url.split('/')[-1]
    file_path = os.path.join(data_dir, filename)
    if os.path.exists(file_path):
        print(f"File '{filename}' already exists.")
        return file_path

    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size_in_bytes = int(r.headers.get('content-length', 0))
            progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    progress_bar.update(len(chunk))
                    f.write(chunk)
            progress_bar.close()
    except HTTPError as e:
        print(f"HTTP Error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    return file_path

def download_geonames():
    data_dir = user_data_dir('geoparser')
    os.makedirs(data_dir, exist_ok=True)

    file_urls = [
        "http://download.geonames.org/export/dump/allCountries.zip",
        "http://download.geonames.org/export/dump/admin1CodesASCII.txt",
        "http://download.geonames.org/export/dump/admin2Codes.txt",
        "http://download.geonames.org/export/dump/countryInfo.txt",
        "http://download.geonames.org/export/dump/featureCodes_en.txt"
    ]

    for url in file_urls:
        file_path = download_file(url, data_dir)
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(data_dir)

def build_geonames_index():
    index = {}
    data_dir = user_data_dir('geoparser')
    geonames_path = os.path.join(data_dir, 'allCountries.txt')
    with open(geonames_path, 'r', encoding='utf-8') as file:
        total_lines = sum(1 for line in file)
    with open(geonames_path, 'r', encoding='utf-8') as file:
        for line in tqdm(file, total=total_lines, desc="Building", unit="lines"):
            columns = line.strip().split('\t')
            geonameid = int(columns[0])
            names = [columns[1]] + columns[3].split(',')
            for name in names:
                normalized_name = normalize_name(name)
                if normalized_name:
                    if normalized_name not in index:
                        index[normalized_name] = set()
                    index[normalized_name].add(geonameid)
    index_file = os.path.join(data_dir, 'index.pkl')
    with open(index_file, 'wb') as file:
        pickle.dump(index, file)

def normalize_name(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r"[^\w\s]", "", name)  # remove all punctuation
    name = re.sub(r"\s+", " ", name).strip()  # normalize whitespaces and strip
    return name.lower()  # convert to lowercase

def download():
    print("Downloading spaCy models...")
    download_spacy_models()
    print("Downloading GeoNames data...")
    download_geonames()
    print("Building GeoNames index...")
    build_geonames_index()

if __name__ == "__main__":
    download()
