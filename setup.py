import pkg_resources
import zipfile
import os
import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        self.download_spacy()
        self.download_geonames()

    def download_spacy(self):
        models = ["en_core_web_sm", "en_core_web_trf"]
        for model in models:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", model])

    def download_geonames(self):
        import requests
        site_packages = os.path.join(sys.prefix, 'lib', 'site-packages')
        data_dir = os.path.join(site_packages, 'geoparser', 'geonames')
        os.makedirs(data_dir, exist_ok=True)

        file_links = [
            "http://download.geonames.org/export/dump/allCountries.zip",
            "http://download.geonames.org/export/dump/admin1CodesASCII.txt",
            "http://download.geonames.org/export/dump/admin2Codes.txt",
            "http://download.geonames.org/export/dump/countryInfo.txt",
            "http://download.geonames.org/export/dump/featureCodes_en.txt"
        ]

        for url in file_links:
            filename = url.split('/')[-1]
            file_path = os.path.join(data_dir, filename)

            response = requests.get(url)
            with open(file_path, 'wb') as f:
                f.write(response.content)

            if filename.endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(data_dir)
                os.remove(file_path)

setup(
    name='geoparser',
    version='0.1.2',
    author='Diego Gomes',
    author_email='diego.gomes@uzh.ch',
    packages=find_packages(),
    description='A geoparsing library for English texts',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'pandas',
        'numpy',
        'spacy',
        'sentence_transformers',
        'tqdm',
        'torch',
        'requests'
    ],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
    ],
    cmdclass={
        'install': PostInstallCommand,
    }
)
