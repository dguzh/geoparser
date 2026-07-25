.. _gazetteers:

Gazetteers
==========

This guide explains what a gazetteer is in this library, which ones ship with it, and how to query them. To build a gazetteer from your own data, see :doc:`custom-gazetteers`.

Overview
--------

The Irchel Geoparser uses gazetteers as the authoritative source of geographic information for toponym resolution. A gazetteer stores information about places, including their names, types, administrative hierarchies, and coordinates. When you mention "Paris" in a text, the gazetteer contains entries for Paris, France; Paris, Texas; Paris, Ontario; and many other places named Paris around the world. Each entry includes not just the name but also attributes like coordinates, population, feature type, and administrative hierarchy that help distinguish one Paris from another.

The library's architecture separates the gazetteer system from the processing modules. Resolvers don't access gazetteers directly through SQL queries or file reads—instead, they use the ``Gazetteer`` class interface which provides standardized search methods.

Every installed gazetteer is a single, self-contained SQLite file (an *artifact*) with a fixed schema shared by all gazetteers: a ``feature`` table (identifier, source, data as JSON, geometry as WKB), a ``name`` table with full-text and phonetic indexes for search, and a small ``metadata`` table. Artifacts are built from declarative YAML configurations by a build pipeline that downloads the source files, stages them in a transient analytical database (DuckDB), and projects them into the canonical schema—including joins, spatial joins, and deduplication. The source files and staging data are discarded after the build; the artifact is the only thing installed, and it is never modified afterwards.

Because artifacts share one schema, all gazetteers behave identically at query time regardless of how heterogeneous their source data is. Geometries are stored in a single coordinate reference system per gazetteer (EPSG:4326 by default); any reprojection happens once, at build time.

Built-in Gazetteers
-------------------

The library includes several built-in gazetteers that cover different geographic scopes and use cases.

GeoNames Cities
~~~~~~~~~~~~~~~

GeoNames Cities is a lightweight alternative to the full GeoNames gazetteer, designed as a quick way to start experimenting with geoparsing. It is built from GeoNames' ``cities500`` dataset (cities with a population of at least 500), supplemented by country and first- and second-level administrative names from GeoNames lookup files.

Only city features include geographic data: coordinates and the full set of place attributes. Countries, admin1 divisions, and admin2 divisions are included as searchable features, but they carry **no geographic data**.

To install GeoNames Cities:

.. code-block:: bash

   python -m geoparser install geonames-cities

Installation typically completes within a few minutes.

This gazetteer omits the vast majority of GeoNames coverage: small towns, neighborhoods, natural features, landmarks, and other place types are not included at all. For real geoparsing beyond a quick trial, install the full GeoNames gazetteer instead.

GeoNames
~~~~~~~~

GeoNames is a comprehensive global gazetteer containing over 13 million place names. It includes entries for countries, administrative divisions, cities, towns, neighborhoods, natural features like mountains and rivers, and points of interest like buildings and monuments. However, the global scope means that coverage varies significantly by region, with some areas having more detailed and up-to-date information than others.

To install GeoNames:

.. code-block:: bash

   python -m geoparser install geonames

The installation process can take a while depending on your system and network speed.

SwissNames3D
~~~~~~~~~~~~

SwissNames3D is a high-quality gazetteer specifically for Switzerland, provided by Swisstopo, the Swiss Federal Office of Topography. It contains detailed information about geographic features within Switzerland, including fine-grained feature classifications and full geometries (points, lines, and polygons). Features are associated with their administrative hierarchy—municipalities, districts, and cantons—via spatial joins computed at build time.

To install SwissNames3D:

.. code-block:: bash

   python -m geoparser install swissnames3d

The installation process typically completes within a few minutes.

Pleiades
~~~~~~~~

Pleiades is a community-built gazetteer of the ancient world, covering the Greek and Roman Mediterranean and its neighbouring regions. It contains some 42,000 places — settlements, regions, rivers, roads, mountains, and peoples — with their names in Latin, ancient Greek, and modern languages, and in the original scripts where attested. Because ancient places have no modern administrative hierarchy, each located place is instead assigned the Roman province its coordinates fall in, computed at build time from a separate boundaries dataset. Places attested in texts but never located are included without geometry, and remain searchable by name.

To install Pleiades:

.. code-block:: bash

   python -m geoparser install pleiades

The installation completes in well under a minute, and the artifact is around 25 MB.

This gazetteer is also the worked example of :doc:`custom-gazetteers`, which builds it up step by step from its published source files.

Managing Installed Gazetteers
-----------------------------

Because each gazetteer is a single file, managing them is simple. List the installed gazetteers and their sizes:

.. code-block:: bash

   python -m geoparser list

Remove a gazetteer you no longer need:

.. code-block:: bash

   python -m geoparser uninstall geonames-cities

Artifacts are stored in your system's user data directory (for example ``~/.local/share/geoparser/gazetteers/`` on Linux); the ``GEOPARSER_GAZETTEERS_DIR`` environment variable overrides this location.

Querying Gazetteers
-------------------

The ``Gazetteer`` class provides a Python interface for querying gazetteer data. This interface is primarily used by resolvers, but you can also use it directly for exploration or custom processing logic.

Initializing a Gazetteer
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a gazetteer instance by specifying its name:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

The gazetteer name must correspond to an installed gazetteer. If the gazetteer isn't installed, an error is raised immediately.

Searching for Features
~~~~~~~~~~~~~~~~~~~~~~

The ``search()`` method finds features matching a given name string. It supports different search methods that trade off precision and recall:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

   # Exact string matching
   features = gazetteer.search("Paris", method="exact")
   print(f"Found {len(features)} features")
   
   for feature in features[:5]:  # Show first 5
       print(f"- {feature.data.get('name')}, {feature.data.get('country_name')}")

The search method parameter controls the matching strategy:

- ``"exact"``: Only returns features whose name exactly matches the search string (case-insensitive and diacritics-insensitive). This is the fastest method but will miss features with slightly different names.

- ``"phrase"``: Returns features whose name contains the search string as a complete phrase. This catches variations like "New York City" when searching for "New York" but is still quite restrictive.

- ``"partial"``: Returns features whose name contains any of the tokens in the search string. This is more flexible and can handle cases where articles or qualifiers are included or omitted, but it may return many candidates.

- ``"fuzzy"``: Uses fuzzy string matching to find features with names similar to the search string, even with spelling variations or typos. This is the most permissive method and generates the most candidates.

For the non-exact search methods, you can specify a ``tiers`` parameter that controls how many rank tiers of results to include. Results are ranked by their match score (BM25 relevance for phrase/partial methods, fuzzy distance for fuzzy method), and tiers group results into brackets of similar scores. Higher tier values include more results but also results with lower match quality:

.. code-block:: python

   # Get only the top-ranked matches
   features = gazetteer.search("London", method="partial", tiers=1)
   
   # Get more permissive results including lower-ranked matches
   features = gazetteer.search("London", method="partial", tiers=3)

Finding Features by Identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you know a feature's identifier, you can retrieve it directly using the ``find()`` method:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

   # Look up Paris, France by its geonameid
   feature = gazetteer.find("2988507")
   
   if feature:
       print(f"Name: {feature.data.get('name')}")
       print(f"Country: {feature.data.get('country_name')}")
       print(f"Population: {feature.data.get('population')}")

The identifier used in ``find()`` should match the identifier scheme used by that gazetteer. For GeoNames, this is the geonameid; for SwissNames3D, it's the UUID.

Working with Features
---------------------

The ``search()`` and ``find()`` methods return ``Feature`` objects that represent individual geographic entities in the gazetteer. Each feature has several important properties:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")
   features = gazetteer.search("Tokyo")
   
   if features:
       feature = features[0]
       
       # The feature's stable identifier
       print(f"ID: {feature.identifier}")
       
       # The source the feature was built from
       print(f"Source: {feature.source}")
       
       # The feature's data as a dictionary
       print(f"Data: {feature.data}")
       
       # The feature's searchable names
       print(f"Names: {feature.names}")
       
       # The feature's geometry as a Shapely object
       print(f"Geometry: {feature.geometry}")
       print(f"Coordinates: ({feature.geometry.x}, {feature.geometry.y})")

The ``identifier`` property contains the identifier that can be used to reference this feature, for example when creating referent annotations. The ``source`` property names the gazetteer source the feature was built from (for example ``allCountries`` in GeoNames, or ``cities500`` / ``countryInfo`` in GeoNames Cities). The ``data`` property is a dictionary containing all the values stored for this feature; features from different sources can have entirely different data. The ``geometry`` property returns a Shapely geometry object in the gazetteer's coordinate reference system (available as ``feature.crs``). Most gazetteers use Point geometries for locations, but this can also be lines, polygons, or multi-part geometries depending on the gazetteer.

The attributes available in the ``data`` dictionary depend on which gazetteer you're using. For GeoNames, common attributes include:

- ``name``: The main name of the feature
- ``latitude`` and ``longitude``: Coordinates in decimal degrees
- ``feature_name``: Human-readable feature type (e.g., "city", "mountain", "stream")
- ``country_name``: Name of the country the feature is in
- ``admin1_name``, ``admin2_name``: First and second-level administrative divisions
- ``population``: Population count for inhabited places
- ``elevation``: Elevation in meters above sea level

For SwissNames3D, attributes include:

- ``NAME``: The name of the feature
- ``OBJEKTART``: Detailed object type in German
- ``GEMEINDE_NAME``: Municipality name
- ``KANTON_NAME``: Canton name
- ``HOEHE``: Elevation in meters

For Pleiades, attributes include:

- ``title``: The main name of the place
- ``place_types``: Its types from the Pleiades vocabulary (e.g. "settlement, urban area")
- ``province``: The Roman province the place falls in
- ``latitude`` and ``longitude``: Coordinates in decimal degrees
- ``location_precision``: How precisely the place is located ("precise" or "rough")
- ``description``: The editors' description of the place
- ``uri``: Link to the place's record on pleiades.stoa.org

The exact data keys are defined per source in the gazetteer's configuration file.

Custom Gazetteers
-----------------

Nothing about the gazetteer system is specific to the datasets above. Any placename data you can describe in a YAML configuration file — a national register, an excavation catalogue, a historical map index, your own field notes — becomes a gazetteer that behaves exactly like a built-in one, with no code to write.

.. code-block:: bash

   python -m geoparser install path/to/my_gazetteer.yaml

:doc:`custom-gazetteers` walks through the whole process on a real dataset, one concern at a time, and documents every configuration key, the choices each one implies, and the problems that come up most often.

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`custom-gazetteers` - Build a gazetteer from your own data
- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.
