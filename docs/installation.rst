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

Installing Gazetteers
---------------------

The library requires gazetteer data to resolve toponyms to geographic locations. Each installed gazetteer is a single, self-contained SQLite file stored in your system's application data directory. You can install gazetteers using a single command that downloads the source data and builds the gazetteer automatically.

.. note::
   The gazetteer CLI command was renamed from ``download`` to ``install``.

.. tip::
   Building a gazetteer can be memory-intensive. We recommend using a machine with at least **4 GB of RAM** and closing other heavy applications so enough memory stays available during the install. Lighter machines may still succeed for smaller gazetteers, but larger builds are more reliable with this headroom.

If you want to try geoparsing quickly, start with **GeoNames Cities**, a lightweight subset that installs in a few minutes. For real geoparsing work, use the full **GeoNames** gazetteer instead: it covers far more than cities alone, including towns, natural features, landmarks, and fine-grained place names that the cities subset omits entirely. **SwissNames3D** covers one country in depth. If none of them fits your work, you can build a gazetteer from your own data; the :ref:`custom-gazetteers` section of the gazetteers guide walks through it end to end.

.. tabs::

   .. tab:: GeoNames Cities

      **GeoNames Cities** is a lightweight GeoNames subset intended for getting started quickly. It includes cities with a population of at least 500. Countries and first- and second-level administrative divisions are also included so that names like "France" or "Bavaria" can be resolved, but those features have **no geographic data**—no coordinates, geometry, or other spatial attributes.

      - **Website**: `geonames.org <https://www.geonames.org/>`_
      - **Coverage**: Global cities (population ≥ 500)
      - **Required Disk Space**: **0.8 GB** during install (installed artifact ≈ **0.3 GB**)
      - **Typical Install Time**: about **1 minute** (varies with hardware and network)
      - **Installation Command**:

      .. code-block:: bash

         python -m geoparser install geonames-cities

      Many place types (towns, rivers, mountains, and so on) are not included at all. Use this gazetteer to experiment with the library; switch to full GeoNames for serious geoparsing.

   .. tab:: GeoNames

      **GeoNames** is a global gazetteer containing over 13 million geographical names covering all countries and territories.

      - **Website**: `geonames.org <https://www.geonames.org/>`_
      - **Coverage**: Global
      - **Required Disk Space**: **30.7 GB** during install (installed artifact ≈ **10.2 GB**)
      - **Typical Install Time**: about **10–15 minutes** (varies with hardware and network)
      - **Installation Command**:

      .. code-block:: bash

         python -m geoparser install geonames

      This command downloads the GeoNames data files, processes them, and builds the gazetteer artifact with its search indices.

   .. tab:: SwissNames3D

      **SwissNames3D** is a high-quality gazetteer for Switzerland provided by Swisstopo, the Swiss Federal Office of Topography.

      - **Website**: `Swisstopo SwissNames3D <https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d>`_
      - **Coverage**: Switzerland
      - **Required Disk Space**: **3.5 GB** during install (installed artifact ≈ **0.7 GB**)
      - **Typical Install Time**: about **1–2 minutes** (varies with hardware and network)
      - **Installation Command**:

      .. code-block:: bash

         python -m geoparser install swissnames3d

      This command downloads the SwissNames3D data, processes it, and builds the gazetteer artifact.

Managing Gazetteers
-------------------

You can list installed gazetteers and remove ones you no longer need:

.. code-block:: bash

   python -m geoparser list
   python -m geoparser uninstall geonames-cities

Data Locations
--------------

Gazetteers and project data are stored in your system's user data directory:

- **Windows**: ``C:\Users\<Username>\AppData\Local\geoparser\``
- **macOS**: ``~/Library/Application Support/geoparser/``
- **Linux**: ``~/.local/share/geoparser/``

Each gazetteer lives in its own SQLite file under the ``gazetteers/`` subdirectory (for example ``gazetteers/geonames.db``); removing one is as simple as deleting the file or running ``python -m geoparser uninstall <name>``. Project data (documents, references, resolutions) is stored separately in ``geoparser.db``, so reinstalling a gazetteer does not affect your projects.

Next Steps
----------

Now that you have installed the Irchel Geoparser, proceed to the :doc:`quickstart` guide to learn how to use the library.
