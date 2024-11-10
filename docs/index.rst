.. _index:

Geoparser
=========

.. note::
   This is the documentation for an upcoming version of Geoparser, which will be released in November this year. It is still a work in progress, so features as well as documentation are subject to change until release. For a documentation of the currently pip installable version of Geoparser please refer to the `Geoparser PyPi page <https://pypi.org/project/geoparser/>`_.

Geoparser is a Python library designed as a complete end-to-end geoparsing pipeline. It integrates advanced natural language processing techniques to recognize and resolve place names (toponyms) in unstructured text, linking them to their corresponding geographical locations.

Overview
--------

Geoparsing involves two main tasks:

- **Toponym Recognition**: Identifying place names in text.
- **Toponym Resolution**: Disambiguating these names to their correct geographical locations.

Geoparser addresses both tasks by combining state-of-the-art natural language processing models and efficient algorithms allowing it to efficiently process large volumes of text with high accuracy.

How It Works
------------

1. **Input Processing**: Users input texts as strings, which are preprocessed using a `spaCy <https://spacy.io/>`_ NLP pipeline. This includes tokenization and named entity recognition to identify toponyms in the form of names of geopolitical entities, locations, and facilities.

2. **Candidate Generation**: For each toponym, the gazetteer database is queried to generate lists of potential candidate locations. This is done using a token-based greedy matching strategy designed to achieve high recall while keeping candidate lists concise.

3. **Textual Representation**: The context surrounding each toponym is extracted and, if necessary, truncated to meet model input length requirements. Candidate locations are also transformed into texts by constructing descriptive sentences using attributes sourced from the gazetteer.

4. **Embedding Generation**: A fine-tuned `SentenceTransformer <https://www.sbert.net/>`_ model is used to encode the textual representations of both toponyms and candidates into embeddings that map them into a shared vector space.

5. **Similarity Comparison**: Embeddings of toponyms and their corresponding candidates are compared using cosine similarity. The candidates with the highest similarity scores are then selected as the most likely locations referenced by the toponyms.

Getting Started
---------------

To begin using Geoparser, refer to the :ref:`installation` and :ref:`usage` sections of this documentation.

Contributing
------------

Geoparser is an open-source project, and contributions are welcome. If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request on the `GitHub repository <https://github.com/dguzh/geoparser>`_.

License
-------

Geoparser is released under the `MIT License <https://opensource.org/licenses/MIT>`_.


.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :hidden:

   installation
   usage

.. toctree::
   :maxdepth: 1
   :caption: Package Reference
   :hidden:

   api/geoparser.geospan
   api/geoparser.geodoc
   api/geoparser.geoparser
   api/geoparser.gazetteers
   api/geoparser.trainer
