.. _installation:

Installation
============

This section provides step-by-step instructions to install and set up Geoparser on your system.

Installing Geoparser
--------------------

You can install Geoparser using ``pip``:

.. code-block:: bash

   pip install geoparser

.. note::
   Geoparser utilizes the ``sentence-transformers`` library, which is built on top of PyTorch. If you have a CUDA-enabled GPU, you can leverage CUDA to significantly speed up geoparsing tasks. Visit the PyTorch `Get Started <https://pytorch.org/get-started/locally/>`_ page and follow the instructions to install PyTorch with CUDA appropriate for your system.

Installing spaCy Models
-----------------------

Geoparser uses spaCy's named entity recognition (NER) functionality for toponym recognition. You will need to download a spaCy model that includes a NER component. spaCy offers models supporting various languages and sizes, optimized for efficiency or accuracy. Visit the `spaCy Models <https://spacy.io/models>`_ page for an overview.

To install a spaCy model (e.g., ``en_core_web_trf``), run:

.. code-block:: bash

   python -m spacy download en_core_web_trf

Installing Gazetteers
---------------------

Geoparser requires gazetteer data to query locations and retrieve related information. Gazetteers are set up in a SQLite database on your system. You can automatically download the necessary data and set up the database with a single command, as shown below.

Currently, Geoparser supports the following gazetteers:

.. tabs::

   .. tab:: GeoNames

      **GeoNames** is a global gazetteer containing over 13 million geographical names.

      - **Website**: `GeoNames website <https://www.geonames.org/>`_
      - **Required Disk Space**: Approximately **3.3 GB**
      - **Installation Command**:

        .. code-block:: bash

           python -m geoparser download geonames

      - **Database Location**:

        - **Windows**: ``C:\Users\<Username>\AppData\Local\geoparser\geonames\geonames.db``
        - **macOS**: ``~/Library/Application Support/geoparser/geonames/geonames.db``
        - **Linux**: ``~/.local/share/geoparser/geonames/geonames.db``

      You can remove the gazetteer data by deleting these files if necessary.

   .. tab:: SwissNames3D

      **SwissNames3D** is a gazetteer for Switzerland provided by Swisstopo.

      - **Website**: `SwissNames3D website <https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d>`_
      - **Required Disk Space**: Approximately **0.2 GB**
      - **Installation Command**:

        .. code-block:: bash

           python -m geoparser download swissnames3d

      - **Database Location**:

        - **Windows**: ``C:\Users\<Username>\AppData\Local\geoparser\swissnames3d\swissnames3d.db``
        - **macOS**: ``~/Library/Application Support/geoparser/swissnames3d/swissnames3d.db``
        - **Linux**: ``~/.local/share/geoparser/swissnames3d/swissnames3d.db``

      You can remove the gazetteer data by deleting these files if necessary.

Next Steps
----------

After installing Geoparser, downloading a spaCy model, and setting up a gazetteer, you are ready to use Geoparser in your projects.

Refer to the :ref:`usage` section for instructions on how to utilize Geoparser.
