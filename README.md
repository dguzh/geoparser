# Geoparser

Geoparser is a Python library for geoparsing English texts. It leverages spaCy for toponym recognition and fine-tuned SentenceTransformer models for toponym resolution.

## Installation

Install Geoparser using pip:

```bash
pip install geoparser
```

## Dependencies

Geoparser depends on the following Python libraries:

- **[appdirs](https://github.com/ActiveState/appdirs)**
- **[numpy](https://numpy.org/)**
- **[pandas](https://pandas.pydata.org/)**
- **[requests](https://requests.readthedocs.io/en/latest/)**
- **[sentence_transformers](https://www.sbert.net/)**
- **[spacy](https://spacy.io/)**
- **[torch](https://pytorch.org/)**
- **[tqdm](https://tqdm.github.io/)**

These dependencies are automatically installed when building Geoparser with pip.

## Download Required Data

After installation, you need to execute the following command to download the necessary files for Geoparser to function:

```bash
python -m geoparser download
```

This command will download the following resources and setup a SQLite database for the GeoNames data:

- **spaCy Models**: Two models are downloaded:
  - `en_core_web_sm`: A less accurate but faster model.
  - `en_core_web_trf`: A more accurate but slower model.
- **GeoNames Data**: The following files are downloaded from GeoNames:
  - [All Countries](http://download.geonames.org/export/dump/allCountries.zip)
  - [Alternate Names](https://download.geonames.org/export/dump/alternateNames.zip)
  - [Admin1 Codes](http://download.geonames.org/export/dump/admin1CodesASCII.txt)
  - [Admin2 Codes](http://download.geonames.org/export/dump/admin2Codes.txt)
  - [Country Info](http://download.geonames.org/export/dump/countryInfo.txt)
  - [Feature Codes](http://download.geonames.org/export/dump/featureCodes_en.txt)

These files are temporarily stored in your system's user-specific data directory during the database setup. Once the database has been populated with the data, the original files are automatically deleted to free up space. The database is then stored in this location:

- **Windows**: `C:\Users\<Username>\AppData\Local\geoparser\geonames.db`
- **macOS**: `~/Library/Application Support/geoparser/geonames.db`
- **Linux**: `~/.local/share/geoparser/geonames.db`

Please ensure you have enough disk space available. The final size of the downloaded GeoNames data will be approximately 3.2 GB, increasing temporarily to 5.5 GB during the download and setup process.

## Usage

### Instantiating the Geoparser

To use Geoparser, you need to instantiate an object of the `Geoparser` class. You can specify which spaCy and transformer model to use, optimising either for accuracy or speed. By default, the library uses accuracy-optimised models:

```python
from geoparser import Geoparser

geo = Geoparser()
```

Default configuration:

```python
geo = Geoparser(spacy_model='en_core_web_trf', transformer_model='dguzh/geo-all-distilroberta-v1')
```

For faster performance, you can opt for the smaller models:

```python
geo = Geoparser(spacy_model='en_core_web_sm', transformer_model='dguzh/geo-all-MiniLM-L6-v2')
```

You can mix and match these models depending on your specific needs. Note that the SentenceTransformer models `dguzh/geo-all-distilroberta-v1` and `dguzh/geo-all-MiniLM-L6-v2` are preliminary versions. Future updates aim to refine these models to improve the accuracy of toponym disambiguation.

### Parsing Texts

Geoparser is optimised for parsing large collections of texts at once. Pass a list of strings to the `parse` method:

```python
docs = geo.parse(["Sample text 1", "Sample text 2", "Sample text 3"])
```

The `parse` method returns a list of `Document` objects, where each `Document` contains a list of `Toponym` objects. Each `Toponym` that is successfully geocoded will have a corresponding `Location` object with the following attributes:

- `geonameid`: The unique identifier for the place in the GeoNames database.
- `name`: The name of the geographical location.
- `admin2_geonameid`: The GeoNames identifier for the second-level administrative division.
- `admin2_name`: The name of the second-level administrative division.
- `admin1_geonameid`: The GeoNames identifier for the first-level administrative division.
- `admin1_name`: The name of the first-level administrative division.
- `country_geonameid`: The GeoNames identifier for the country.
- `country_name`: The name of the country.
- `feature_name`: The type of geographical feature (e.g., mountain, lake).
- `latitude`: The latitude of the location.
- `longitude`: The longitude of the location.
- `elevation`: The elevation of the location in meters.
- `population`: The population of the location.

## Example

Here's an example illustrating how the library might be used:

```python
from geoparser import Geoparser

geo = Geoparser()

text = "Zurich is a city rich in history."

docs = geo.parse([text])

for doc in docs:
    for toponym in doc.toponyms:
        if toponym.location:
            print(toponym, "->", toponym.location)
```
