Geoparser
=========

.. note::
   This is the documentation for an upcoming version of Geoparser, which will be released in November this year. It is still a work in progress, so features as well as documentation are subject to change until release. For a documentation of the currently pip installable version of Geoparser please refer to the `Geoparser PyPi page <https://pypi.org/project/geoparser/>`_.

Geoparser is a Python library designed for efficient and adaptable geoparsing using transformer models. It provides an end-to-end geoparsing pipeline that integrates toponym recognition and disambiguation, allowing users to extract and link location mentions in text to their corresponding geographical locations in a gazetteer.

Key Features
------------

- **Toponym Recognition**: Identifies location names in text using spaCy's Named Entity Recognition.
- **Toponym Resolution**: Resolves ambiguous toponyms to their correct geographical locations using a fine-tuned SentenceTransformer model.
- **Customizable Pipeline**: Easily adaptable to different text types, languages, and gazetteers.
- **Extensible Gazetteer Support**: Integrates with gazetteers like GeoNames and can be extended to others.
- **Training Module**: Allows fine-tuning of models for specific domains or text corpora.

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
