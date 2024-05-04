import os
import sys
import requests
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
                print(f"Downloaded spaCy model '{model}'.")
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while downloading spaCy model '{model}': {e}")
                sys.exit(1)
        else:
            print(f"Model '{model}' already exists.")

def download_file(url, data_dir):
    filename = url.split('/')[-1]
    file_path = os.path.join(data_dir, filename)
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
            print(f"Downloaded '{filename}'.")
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
        "https://download.geonames.org/export/dump/alternateNames.zip",
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
            os.remove(file_path)

def main():

    print("Downloading spaCy models...")
    download_spacy_models()
    
    print("Downloading GeoNames data...")
    download_geonames()

if __name__ == "__main__":
    main()