# Geoparser

Geoparser is a Python library for geoparsing English texts. It leverages spaCy for toponym recognition and tine-tuned SentenceTransformer models for toponym resolution.

## Installation

Install Geoparser using pip:

```bash
pip install geoparser
```

## Download Required Data

After installation, you need to download the necessary data files for Geoparser to function properly:

```bash
python -m geoparser download
```

This command will download the following resources:

- **spaCy Models**: Two models are downloaded:
  - `en_core_web_sm`: A less accurate but faster model.
  - `en_core_web_trf`: A more accurate but slower model.
- **GeoNames Data**: The following files are downloaded from GeoNames:
  - [All Countries](http://download.geonames.org/export/dump/allCountries.zip)
  - [Admin1 Codes](http://download.geonames.org/export/dump/admin1CodesASCII.txt)
  - [Admin2 Codes](http://download.geonames.org/export/dump/admin2Codes.txt)
  - [Country Info](http://download.geonames.org/export/dump/countryInfo.txt)
  - [Feature Codes](http://download.geonames.org/export/dump/featureCodes_en.txt)

These files are stored in the user-specific data directory:

- **Windows**: `C:\Users\<Username>\AppData\Local\geoparser\`
- **macOS**: `~/Library/Application Support/geoparser/`
- **Linux**: `~/.local/share/geoparser/`

Please ensure you have adequate disk space available, as the total size of these files is approximately 2.3 GB.

## Usage

### Instantiating the Geoparser

To use Geoparser, you need to instantiate an object of the `Geoparser` class. You can specify which spaCy and transformer model to use, optimizing either for accuracy or speed. By default, the library uses accuracy-optimized models:

```python
from geoparser import Geoparser

geo = Geoparser()
```

For faster performance, you can opt for the smaller models:

```python
geo = Geoparser(spacy_model='en_core_web_sm', transformer_model='dguzh/geo-all-MiniLM-L6-v2')
```

You can mix and match these models depending on your specific needs. Note that the transformer models `dguzh/geo-all-distilroberta-v1` and `dguzh/geo-all-MiniLM-L6-v2` are preliminary versions. Future updates aim to refine these models to improve the accuracy of toponym disambiguation.

### Parsing Texts

Geoparser is optimized for parsing large collections of texts at once. Pass a list of strings to the `parse` method:

```python
docs = geo.parse(["Sample text 1", "Sample text 2", "Sample text 3"])
```

The `parse` method returns a list of `Document` objects, where each `Document` contains a list of `Toponym` objects. Each `Toponym` that is successfully geocoded will have a corresponding `Location` object with detailed geographical data:

### Location Attributes

Each `Location` object has the following attributes:

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

Here's an example showing how the library might be used:

```python
text = "Zurich is a city rich in history."
docs = geo.parse([text])

for doc in docs:
    for toponym in doc.toponyms:
        if toponym.location:
            print(toponym, "->", toponym.location)
```
