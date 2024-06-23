# Geoparser

Geoparser is a Python library for geoparsing unstructured texts. It employs spaCy for toponym recognition and fine-tuned SentenceTransformer models for toponym resolution.

## Installation

Install Geoparser using pip:

```bash
pip install geoparser
```

### Dependencies

Geoparser depends on the following Python libraries:

- **[accelerate](https://github.com/huggingface/accelerate)**
- **[appdirs](https://github.com/ActiveState/appdirs)**
- **[datasets](https://github.com/huggingface/datasets)**
- **[haversine](https://github.com/mapado/haversine)**
- **[numpy](https://numpy.org/)**
- **[pandas](https://pandas.pydata.org/)**
- **[requests](https://requests.readthedocs.io/en/latest/)**
- **[sentence_transformers](https://www.sbert.net/)**
- **[spacy](https://spacy.io/)**
- **[torch](https://pytorch.org/)**
- **[tqdm](https://tqdm.github.io/)**

These dependencies are automatically installed when building Geoparser with pip.

**GPU support:** The performance of Geoparser benefits greatly from GPU processing. If you have a CUDA enabled GPU available, you can use it for toponym recognition with spaCy's transformer models as well as for toponym resolution using the SentenceTransformers models. To do so, install [PyTorch with CUDA support](https://pytorch.org/get-started/locally/) as well as the [GPU enabled version of spaCy](https://spacy.io/usage#gpu). 

## Download Required Data

To get started with Geoparser, specific data resources must be downloaded:

### spaCy Models

You should manually download the desired spaCy model based on your specific needs. For example, to download the default recommended model for English texts, run:

```bash
python -m spacy download en_core_web_trf
```

For an overview of available spaCy models, visit the [spaCy models documentation](https://spacy.io/usage/models).

### Gazetteer Data

Geoparser uses gazetteer data to resolve toponyms to geographic locations. The default gazetteer is GeoNames, and it can be set up with the following command:

```bash
python -m geoparser download geonames
```

This command downloads and sets up a SQLite database with GeoNames data necessary for geoparsing. The following files are downloaded from GeoNames:
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

Please ensure you have enough disk space available. The final size of the downloaded GeoNames data will be approximately 3.2 GB, increasing temporarily to around 5 GB during the download and setup process.

**Note:** The library currently only supports the GeoNames gazetteer, but the framework allows for future extensions with other knowledge bases.

## Usage

### Instantiating the Geoparser

To use Geoparser, instantiate an object of the `Geoparser` class with optional specifications for the spaCy model, transformer model, and gazetteer. By default, the library uses an accuracy-optimised configuration:

```python
from geoparser import Geoparser

geo = Geoparser()
```

Default configuration:

```python
geo = Geoparser(spacy_model='en_core_web_trf', transformer_model='dguzh/geo-all-distilroberta-v1', gazetteer='geonames')
```

For faster performance, you may opt for more lightweight models:

```python
geo = Geoparser(spacy_model='en_core_web_sm', transformer_model='dguzh/geo-all-MiniLM-L6-v2', gazetteer='geonames')
```

You can mix and match these models depending on your specific needs. Note that the SentenceTransformer models `dguzh/geo-all-distilroberta-v1` and `dguzh/geo-all-MiniLM-L6-v2` are preliminary versions. Future updates aim to refine these models to improve the accuracy of toponym disambiguation.

### Parsing Texts

Geoparser is optimised for parsing large collections of texts at once. To perform parsing, supply a list of strings to the `parse` method. This method processes the input and returns a list of `GeoDoc` objects, each containing identified and resolved toponyms:

```python
docs = geo.parse(["Sample text 1", "Sample text 2", "Sample text 3"])
```

The `GeoDoc` class extends spaCy's `Doc` class, inheriting all its functionalities. You can access the toponyms identified in each document through `GeoDoc.toponyms`, which returns a tuple of `GeoSpan` objects representing the toponyms in the document. The `GeoSpan` class is an extension of spaCy's `Span` class and inherits all its functionalities:

```python
for doc in docs:
    for toponym in doc.toponyms:
        print(toponym, toponym.start_char, toponym.end_char)
```

Toponyms are resolved to their corresponding geographical location which can be accessed using `GeoSpan.location`. This returns a dictionary with geographic data sourced from the gazetteer:

```python
for doc in docs:
    for toponym in doc.toponyms:
        if toponym.location:
            print(toponym, toponym.location['geonameid'], toponym.location['latitude'], toponym.location['longitude'])
```

Example of a location dictionary using the GeoNames gazetteer:

```python
{
'geonameid': 2867714,
'name': 'Munich',
'admin2_geonameid': 2861322,
'admin2_name': 'Upper Bavaria',
'admin1_geonameid': 2951839,
'admin1_name': 'Bavaria',
'country_geonameid': 2921044,
'country_name': 'Germany',
'feature_name': 'seat of a first-order administrative division',
'latitude': 48.13743,
'longitude': 11.57549,
'elevation': None,
'population': 1260391
}
```

The certainty of the toponym resolution predictions can be retrieved using the `GeoSpan.score` property. Users may choose to only consider predictions above a certain threshold as valid.

For document-wise retrieval of location data you may want to use the `GeoDoc.locations` attribute to retrieve lists of location dictionaries aligned with `GeoDoc.toponyms`. This allows for more efficient batch retrieval of location data, reducing the number of database queries:

- To get a list of location dictionaries of all toponyms in a document:
```python
all_locations = doc.locations
```
- To retrieve specific attributes:
```python
all_geonameids = doc.locations['geonameid']
```
- To retrieve multiple attributes:
```python
all_coordinates = doc.locations['latitude', 'longitude']
```

### Geocoding Scope

You can limit the scope of geocoding by specifying one or more countries and [GeoNames feature classes](https://www.geonames.org/export/codes.html). This ensures that Geoparser only encodes locations within the specified countries, and can limit the types of geographical features to consider. To use this feature, use the `country_filter` and `feature_filter` parameters in the `parse` method:

```python
docs = geo.parse(texts, country_filter=['CH', 'DE', 'AT'], feature_filter=['A', 'P'])
```

### Example

Here's an example illustrating how the Geoparser might be used:

```python
from geoparser import Geoparser

geo = Geoparser()

texts = [
    "Zurich is a city rich in history.",
    "Geneva is known for its role in international diplomacy.",
    "Munich is famous for its annual Oktoberfest celebration."
]    

docs = geo.parse(texts)

for doc in docs:
    identifiers = doc.locations['name', 'admin1_name', 'country_name']
    for toponym, identifier in zip(doc.toponyms, identifiers):
        print(toponym, "->", identifier)
```

## Training Custom Geoparser Models

The `GeoparserTrainer` is an extension of the `Geoparser` class designed for training and evaluating geoparsing models with custom datasets. This allows users to fine-tune transformer models specific to their texts or domains.

### Fine-Tuning HuggingFace Models for Geoparsing

The `GeoparserTrainer` supports fine-tuning any transformer model from HuggingFace that is compatible with the SentenceTransformers framework. This allows users to leverage a wide range of pre-trained models to enhance geoparsing capabilities tailored to specific needs.

While it is possible to fine-tune virtually any HuggingFace model that works within the SentenceTransformers ecosystem, the employed geoparsing strategy benefits from models that are pre-trained on sentence similarity tasks. For an overview of pre-trained SentenceTransformer models that are optimised for tasks like sentence similarity, please refer to the [official SentenceTransformers documentation](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html#original-models).

### Preparing Your Dataset

To train a custom geoparser model, you need to prepare a dataset formatted as a list of tuples, where each tuple contains a text string and an associated list of annotations. Annotations should be tuples of (start character, end character, location id) that mark the toponyms within the text:

```python
train_corpus = [
    ("Zurich is a city in Switzerland.", [(0, 6, 2657896), (20, 31, 2658434)]),
    ("Geneva is known for international diplomacy.", [(0, 6, 2660646)]),
    ("Munich hosts the annual Oktoberfest.", [(0, 6, 2867714)])
]
```

### Annotating and Preparing Training Data

Once you have your dataset, use the `annotate` method to convert the text and annotations into gold `GeoDoc` objects suitable for training:

```python
from geoparser import GeoparserTrainer

trainer = GeoparserTrainer(transformer_model="bert-base-uncased")

train_docs = trainer.annotate(train_corpus)
```

### Training the Model

You can then train a model using the prepared documents:

```python
output_path = "path_to_custom_model"

trainer.train(train_docs, output_path=output_path)
```

### Evaluating the Model

After training, you can use the fine-tuned model to resolve toponyms in a test set and evaluate how well your model performed:

```python
test_corpus = [
    ...
]

test_docs = trainer.annotate(test_corpus)

trainer.resolve(test_docs)

evaluation_results = trainer.evaluate(test_docs)

print(evaluation_results)
```

This compares the predicted location IDs against the annotated IDs and provides the following metrics:
- Exact match accuracy
- Accuracy within a 161 km radius
- Mean error distance [km]
- Area under the curve

### Using the Trained Model

Once trained, you can use your custom model to parse new texts by specifying the trained transformer model's path when instantiating `Geoparser`:

```python
from geoparser import Geoparser

geo = Geoparser(transformer_model="path_to_custom_model")

docs = geo.parse(["New text to parse"])
```
