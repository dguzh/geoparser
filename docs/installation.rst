.. _installation:

Installation
============

This guide provides step-by-step instructions to install and set up the Irchel Geoparser on your system.

Installing the Library
----------------------

Install the Irchel Geoparser using pip:

.. code-block:: bash

   pip install geoparser

.. warning::
   **macOS users**: The Irchel Geoparser requires Python with SQLite extension loading support, which is **not available** in the default macOS system Python or Python installed from the official Python website. You must use Python installed via Homebrew.
   
   See the :doc:`macos_compatibility` guide for detailed setup instructions.

.. note::
   The library uses PyTorch through the sentence-transformers package. If you have a CUDA-enabled GPU, you can significantly speed up geoparsing tasks by installing PyTorch with CUDA support. Visit the PyTorch `Get Started <https://pytorch.org/get-started/locally/>`_ page and follow the instructions appropriate for your system.

Installing Gazetteers
---------------------

The library requires gazetteer data to resolve toponyms to geographic locations. Gazetteers are stored in a SQLite database in your system's application data directory. You can install gazetteers using a single command that downloads the data and sets up the database automatically.

.. tabs::

   .. tab:: GeoNames

      **GeoNames** is a global gazetteer containing over 13 million geographical names covering all countries and territories.

      - **Website**: `geonames.org <https://www.geonames.org/>`_
      - **Coverage**: Global
      - **Required Disk Space**: Approximately **13 GB**
      - **Installation Command**:

      .. code-block:: bash

         python -m geoparser download geonames

      This command downloads the GeoNames data files, processes them, and creates the necessary database tables and indices. The process may take 15-30 minutes depending on your system.

   .. tab:: SwissNames3D

      **SwissNames3D** is a high-quality gazetteer for Switzerland provided by Swisstopo, the Swiss Federal Office of Topography.

      - **Website**: `Swisstopo SwissNames3D <https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d>`_
      - **Coverage**: Switzerland
      - **Required Disk Space**: Approximately **1.2 GB**
      - **Installation Command**:

      .. code-block:: bash

         python -m geoparser download swissnames3d

      This command downloads the SwissNames3D data, processes it, and creates the database. The process typically completes within a few minutes.

Database Location
-----------------

All gazetteer data and project information is stored in a centralized SQLite database located in your system's user data directory:

- **Windows**: ``C:\Users\<Username>\AppData\Local\geoparser\geoparser.db``
- **macOS**: ``~/Library/Application Support/geoparser/geoparser.db``
- **Linux**: ``~/.local/share/geoparser/geoparser.db``

You can remove all data by deleting this database file. Note that this will remove all gazetteers and any projects you have created.

Next Steps
----------

Now that you have installed the Irchel Geoparser, proceed to the :doc:`quickstart` guide to learn how to use the library.
