.. _installation:

Installation
============

This guide provides step-by-step instructions to install and set up the Irchel Geoparser on your system.

Installing the Library
----------------------

Install the Irchel Geoparser using pip:

.. code-block:: bash

   pip install geoparser

.. note::
   The library uses PyTorch through the sentence-transformers package. If you have a CUDA-enabled GPU, you can significantly speed up geoparsing tasks by installing PyTorch with CUDA support. Visit the PyTorch `Get Started <https://pytorch.org/get-started/locally/>`_ page and follow the instructions appropriate for your system.

Installing spaCy Models
-----------------------

The library uses spaCy for named entity recognition in the default recognizer module. You need to download at least one spaCy model that includes a named entity recognition component. spaCy offers models for various languages with different size and accuracy tradeoffs. Visit the `spaCy Models <https://spacy.io/models>`_ page for a complete overview.

To install the default English model, run:

.. code-block:: bash

   python -m spacy download en_core_web_sm

For better accuracy at the cost of speed and memory, consider the transformer-based model:

.. code-block:: bash

   python -m spacy download en_core_web_trf

If you need to process texts in other languages, install the appropriate spaCy model for that language.

Installing Gazetteers
---------------------

The library requires gazetteer data to resolve toponyms to geographic locations. Gazetteers are stored in a SQLite database in your system's application data directory. You can install gazetteers using a single command that downloads the data and sets up the database automatically.

The library currently supports two gazetteers:

GeoNames
~~~~~~~~

**GeoNames** is a global gazetteer containing over 13 million geographical names covering all countries and territories.

- **Website**: `geonames.org <https://www.geonames.org/>`_
- **Coverage**: Global
- **Required Disk Space**: Approximately **3.3 GB**
- **Installation Command**:

.. code-block:: bash

   python -m geoparser download geonames

This command downloads the GeoNames data files, processes them, and creates the necessary database tables and indices. The process may take 15-30 minutes depending on your system.

SwissNames3D
~~~~~~~~~~~~

**SwissNames3D** is a high-quality gazetteer for Switzerland provided by Swisstopo, the Swiss Federal Office of Topography.

- **Website**: `Swisstopo SwissNames3D <https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d>`_
- **Coverage**: Switzerland
- **Required Disk Space**: Approximately **0.2 GB**
- **Installation Command**:

.. code-block:: bash

   python -m geoparser download swissnames3d

This command downloads the SwissNames3D data, processes it, and creates the database. The process typically completes within a few minutes.

Database Location
~~~~~~~~~~~~~~~~~

All gazetteer data is stored in a centralized SQLite database located in your system's user data directory:

- **Windows**: ``C:\Users\<Username>\AppData\Local\geoparser\geoparser.db``
- **macOS**: ``~/Library/Application Support/geoparser/geoparser.db``
- **Linux**: ``~/.local/share/geoparser/geoparser.db``

You can remove gazetteer data by deleting this database file. Note that this will remove all gazetteers and any projects you have created.

Verifying Installation
----------------------

After completing the installation steps, you can verify that everything is working correctly by running a simple test:

.. code-block:: python

   from geoparser import Geoparser
   
   geoparser = Geoparser()
   documents = geoparser.parse("Paris is the capital of France.")
   
   for doc in documents:
       for toponym in doc.toponyms:
           if toponym.location:
               print(f"{toponym.text} -> {toponym.location.data.get('name')}")

If the installation is successful, this should print something like:

.. code-block:: text

   Paris -> Paris
   France -> France

Next Steps
----------

Now that you have installed the Irchel Geoparser, proceed to the :doc:`quickstart` guide to learn how to use the library for basic geoparsing tasks.
