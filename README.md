# Irchel Geoparser

<p align="center">
<a href="https://github.com/dguzh/geoparser/actions?query=event%3Apush+branch%3Amain+workflow%3ACI" target="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/dguzh/geoparser/ci.yml?branch=main&logo=github&label=CI" alt="CI status">
</a>
<a href="https://github.com/dguzh/geoparser/actions/workflows/test.yml?query=branch%3Amain+" target="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/dguzh/geoparser/test.yml?branch=main&logo=github&label=Tests" alt="Tests">
</a>
<a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/dguzh/geoparser" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/dguzh/geoparser.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/geoparser" target="_blank">
    <img src="https://img.shields.io/pypi/v/geoparser?&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/geoparser" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/geoparser" alt="Supported Python versions">
</a>
</p>

The **Irchel Geoparser** (hereafter referred to simply as **Geoparser**) is a Python library designed as a complete end-to-end geoparsing pipeline. It integrates advanced natural language processing techniques to recognize and resolve place names (toponyms) in unstructured text, linking them to their corresponding geographical locations.

## Overview

Geoparsing involves two main tasks:

- **Toponym Recognition**: Identifying place names in text.
- **Toponym Resolution**: Disambiguating these names to their correct geographical locations.

Geoparser addresses both tasks by combining state-of-the-art language models and efficient algorithms, enabling it to process large volumes of text with high accuracy and speed.

## How It Works

1. **Input Processing**: Users input texts as strings, which are preprocessed using a [spaCy](https://spacy.io/) NLP pipeline. This includes tokenization and named entity recognition to identify toponyms in the form of names of geopolitical entities, locations, and facilities.

2. **Candidate Generation**: For each toponym, the gazetteer database is queried to generate lists of potential candidate locations. This is done using a token-based greedy matching strategy designed to achieve high recall while keeping candidate lists concise.

3. **Textual Representation**: Toponyms are represented using their surrounding context, which is extracted and truncated to meet model input length requirements. Candidate locations are also transformed into text by constructing descriptive sentences using attributes sourced from the gazetteer.

4. **Embedding Generation**: A fine-tuned [SentenceTransformer](https://www.sbert.net/) model is used to encode the textual representations of both the toponyms and their corresponding candidates into embeddings, mapping them into a shared vector space.

5. **Similarity Comparison**: Embeddings of toponyms and their corresponding candidates are compared using cosine similarity. The candidates with the highest similarity scores are then selected as the most likely locations referenced by the toponyms.

## Getting Started

To begin using Geoparser, refer to the [installation](https://docs.geoparser.app/en/latest/installation.html) and [usage](https://docs.geoparser.app/en/latest/usage.html) sections of the [documentation](https://docs.geoparser.app/en/latest/).

## Contributing

Geoparser is an open-source project, and contributions are welcome. If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request on the [GitHub repository](https://github.com/dguzh/geoparser).

## Acknowledgments

Geoparser originated as part of my Master's thesis and was further developed with support from the [Department of Geography at the University of Zurich](https://www.geo.uzh.ch/). I thank my supervisor, Prof. Dr. Ross Purves, for his insightful feedback, encouragement, and the opportunity to continue this work as part of a research project.

## License

Geoparser is released under the [MIT License](https://github.com/dguzh/geoparser/blob/main/LICENSE). It also uses several third-party libraries, each with its own license. For a complete list of these licenses, see the [full license details](https://github.com/dguzh/geoparser/blob/main/THIRD_PARTY_LICENSES) in the repository.
