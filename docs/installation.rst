.. _installation:

Installation
============

Setting up the Irchel Geoparser takes two steps: installing the Python package, and installing a gazetteer for it to resolve place names against. Both are covered here, and you need both before you can parse anything.

The package needs **Python 3.10 or newer** and about **3 GB of disk space**, most of which is PyTorch. A gazetteer needs considerably more, and how much depends on which one you choose.

Installing the Package
----------------------

We recommend installing into a virtual environment, so that the library and its dependencies cannot disturb anything else on your machine.

.. tabs::

   .. tab:: macOS / Linux

      .. code-block:: bash

         python3 -m venv geoparser-env

      .. code-block:: bash

         source geoparser-env/bin/activate

      .. code-block:: bash

         pip install geoparser

   .. tab:: Windows

      .. code-block:: powershell

         python -m venv geoparser-env

      .. code-block:: powershell

         geoparser-env\Scripts\activate

      .. code-block:: powershell

         pip install geoparser

The install downloads roughly 3 GB and takes a few minutes. A quiet pause while pip resolves versions is normal.

Once the environment is activated your prompt starts with ``(geoparser-env)``. The environment is active only in that terminal, so activate it again in any new one — that is the usual explanation for a ``ModuleNotFoundError: No module named 'geoparser'`` after a successful install. Run ``deactivate`` to leave it.

To confirm the package is installed and reachable:

.. code-block:: bash

   python -m geoparser list

.. code-block:: text

   No gazetteers installed.

That is expected at this point: the package is installed, but there is no gazetteer yet.

Installing a Gazetteer
----------------------

A geoparser answers two questions about a text: which words are place names, and which places those names refer to. The Irchel Geoparser answers the second by choosing from the entries of a **gazetteer** — a database of places with their names, coordinates, and attributes. Recognizing that "Springfield" is a place name takes only the text, but deciding *which* Springfield it is, and attaching coordinates to it, means picking from a set of candidate places.

So a gazetteer is a required part of the setup here. It is not the only conceivable design — some approaches predict coordinates directly from the text, without a set of candidates — but it is the design in this library, and nothing will resolve until you have installed one.

Gazetteers are large, they come from third parties under their own licences, and which one you want depends on what you are studying, so none is included with the package. You install one yourself, once, with a single command.

Choosing One
~~~~~~~~~~~~

The library includes ready-made configurations for two gazetteers, so either can be installed without writing one. **GeoNames** is the one to install unless you have a specific reason not to: it is global, it covers all kinds of places, and it is what the library's default models are tuned for. **SwissNames3D** is worth choosing if your material is Swiss, because it describes that one country in far more detail than GeoNames does. You can install both and choose between them per resolver; they do not interfere with each other.

.. tabs::

   .. tab:: GeoNames

      **The recommended choice.** A global gazetteer of over 13 million names, covering countries, administrative divisions, cities, towns, neighbourhoods, natural features such as mountains and rivers, and points of interest such as buildings and monuments. The library's default resolver models are fine-tuned against it, so it is what everything else in this documentation assumes.

      - **Website**: `geonames.org <https://www.geonames.org/>`_
      - **Licence**: CC BY 4.0
      - **Coverage**: Global, all place types
      - **Disk space**: **30.7 GB free needed during install**; the installed file is about **10.2 GB**
      - **Install time**: about **10–15 minutes**, depending on hardware and network

      .. code-block:: bash

         python -m geoparser install geonames

      Coverage varies by region — some parts of the world are described in far more detail than others.

   .. tab:: SwissNames3D

      **For Swiss material.** The official Swiss placename register from Swisstopo, the Federal Office of Topography. Much finer-grained than GeoNames within Switzerland, with detailed feature classifications and full geometries — points, lines, and polygons — and each feature linked to its municipality, district, and canton.

      - **Website**: `Swisstopo SwissNames3D <https://www.swisstopo.admin.ch/en/landscape-model-swissnames3d>`_
      - **Coverage**: Switzerland only
      - **Disk space**: **3.5 GB free needed during install**; the installed file is about **0.7 GB**
      - **Install time**: about **1–2 minutes**

      .. code-block:: bash

         python -m geoparser install swissnames3d

      Attribute names are in German (``NAME``, ``OBJEKTART``, ``KANTON_NAME``). Note that the default resolver models were trained on English text against GeoNames, so expect to lower ``min_similarity`` and, ideally, to fine-tune — see :doc:`guides/training`.

If you work on a region, a period, or a domain that neither covers, you can build a gazetteer from your own data — see :doc:`guides/custom-gazetteers`.

Running the Install
~~~~~~~~~~~~~~~~~~~

Taking GeoNames as the example:

.. code-block:: bash

   python -m geoparser install geonames

The command downloads the source data, transforms it, and builds a single self-contained file. It reports three stages:

.. code-block:: text

   ─────────────────────────────────── geonames ───────────────────────────────────

   Prepared sources                          ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:08:42
   Compiled features                         ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:03:11
   Built artifact                            ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:02:35

   Summary

   Features  13,041,196
   Names     19,483,772

When the summary prints, the gazetteer is installed and ready to use.

The build needs considerably more disk space than the finished file occupies, because the source data is staged before being compacted; free space is checked before the build starts, and the intermediate files are deleted when it finishes. It also needs about 4 GB of RAM, so closing other heavy applications helps. If a build fails, any previously installed gazetteer of the same name is left as it was, so it is safe to simply run the command again.

Once a gazetteer is installed, ``list`` reports it with its size on disk:

.. code-block:: bash

   python -m geoparser list

.. code-block:: text

   geonames  (9700.7 MB)

Sizes shift as the upstream data is updated, so treat that as indicative. To remove one you no longer need:

.. code-block:: bash

   python -m geoparser uninstall geonames

.. code-block:: text

   Removed gazetteer 'geonames'.

Checking the Gazetteer
~~~~~~~~~~~~~~~~~~~~~~

To confirm the gazetteer is queryable before writing any pipeline code:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")
   results = gazetteer.search("Paris", method="exact")

   print(f"{len(results)} places named Paris")
   for feature in results[:3]:
       print(" ", feature.data.get("name"), "|", feature.data.get("country_name"))

.. code-block:: text

   122 places named Paris
     Paris | Spain
     Paris | Spain
     Paris | Armenia

Both the number of results and the absence of the French capital from the top of the list are expected. Place names are ambiguous, and GeoNames records 122 distinct places called Paris; ``search()`` returns all of them in no particular order, since it has no notion of which is the most prominent. Choosing between candidates like these, using the context a name appeared in, is the job of a resolver — the subject of :doc:`concepts`.

Using a GPU
-----------

Everything in this documentation works on a CPU. If you have an NVIDIA GPU, recognition and resolution run substantially faster on it, and the PyTorch build that ``pip`` selects on Linux and Windows is normally CUDA-enabled already. To check that your GPU is visible:

.. code-block:: bash

   python -c "import torch; print(torch.cuda.is_available())"

If that prints ``False`` and you do have a compatible card, reinstall PyTorch following the instructions for your CUDA version on the PyTorch `Get Started <https://pytorch.org/get-started/locally/>`_ page. On Apple Silicon, PyTorch uses the Metal backend and no extra step is needed.

Working in Jupyter
------------------

Install Jupyter into the same environment, otherwise the notebook runs against a different Python and will not find the library:

.. code-block:: bash

   pip install jupyter

.. code-block:: bash

   python -m ipykernel install --user --name geoparser-env --display-name "Python (geoparser)"

.. code-block:: bash

   jupyter lab

Then choose the "Python (geoparser)" kernel. ``import sys; print(sys.executable)`` inside the notebook should print a path inside ``geoparser-env``.

.. _installation-data:

Where Data Is Stored
--------------------

Gazetteers and project data are kept outside your working directory, in your operating system's standard location for application data:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Platform
     - Location
   * - **Windows**
     - ``C:\Users\<Username>\AppData\Local\geoparser\``
   * - **macOS**
     - ``~/Library/Application Support/geoparser/``
   * - **Linux**
     - ``~/.local/share/geoparser/``

Each gazetteer is one self-contained file under ``gazetteers/``, and your projects, documents, and results live separately in ``geoparser.db``. Because they are separate, reinstalling a gazetteer does not touch your projects, and deleting a project does not affect your gazetteers. A gazetteer can also be backed up or moved between machines by copying its file.

Upgrading
---------

.. code-block:: bash

   pip install --upgrade geoparser

.. warning::

   The database format is not yet stable between releases. If you upgrade and your project database was written by an older version, the library will refuse to open it and tell you so. There is no automatic migration yet: you will need to delete ``geoparser.db``, which loses stored projects and results. Export anything you want to keep first — see :doc:`guides/results`.

To remove everything, delete the environment folder, and the data directory above if you want the gazetteers and projects gone as well. Nothing is installed anywhere else.

Next Steps
----------

Setup is complete. Parse your first text in the :doc:`quickstart`.
