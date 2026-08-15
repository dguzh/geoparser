.. _gazetteers:

Querying Gazetteers
===================

A gazetteer is the list of places a resolver chooses from. This guide explains what one contains, how the pre-configured gazetteers differ, and how to query them directly from Python. Installing one is covered in :doc:`../installation`, and building one from your own data in :doc:`custom-gazetteers`.

What a Gazetteer Is
-------------------

The Irchel Geoparser uses gazetteers as the authoritative source of geographic information for toponym resolution. A gazetteer stores information about places: their names, types, administrative hierarchies, and coordinates. When a text mentions "Paris", the gazetteer holds entries for Paris, France; Paris, Texas; Paris, Ontario; and many others. Each entry carries not just the name but attributes — coordinates, population, feature type, administrative hierarchy — that are what make it possible to tell one Paris from another.

The library keeps gazetteers separate from the processing modules. Resolvers never reach into a gazetteer with SQL or file reads; they go through the ``Gazetteer`` class, which offers a small set of search methods. That boundary is what lets any gazetteer work with any resolver.

Every installed gazetteer is a single, self-contained SQLite file — an *artifact* — with a fixed schema shared by all gazetteers: a ``feature`` table (identifier, source, data as JSON, geometry as WKB), a ``name`` table with full-text and phonetic indexes for search, and a small ``metadata`` table. Artifacts are built from declarative YAML configurations by a pipeline that downloads the source files, stages them in a transient analytical database (DuckDB), and projects them into the canonical schema — including joins, spatial joins, and deduplication. The source files and staging data are discarded after the build; the artifact is the only thing installed, and it is never modified afterwards.

Because artifacts share one schema, all gazetteers behave identically at query time regardless of how heterogeneous their source data is. Geometries are stored in a single coordinate reference system per gazetteer (EPSG:4326 by default); any reprojection happens once, at build time.

The Pre-configured Gazetteers
-----------------------------

The library includes ready-made configurations for two gazetteers, so either can be installed without writing one. Install them as described in :doc:`../installation`; what follows is what you get.

GeoNames
~~~~~~~~

A comprehensive global gazetteer of over 13 million place names, covering countries, administrative divisions, cities, towns, neighborhoods, natural features such as mountains and rivers, and points of interest such as buildings and monuments. It is the gazetteer the default resolver models were trained against, and the one to use for real work.

Its global scope comes with uneven coverage: some regions are described in far more detail, and kept more current, than others. Consider what that means for your material before drawing conclusions from how much resolved.

SwissNames3D
~~~~~~~~~~~~

The official Swiss placename register from Swisstopo, the Federal Office of Topography. Within Switzerland it is far richer than GeoNames: fine-grained feature classifications and full geometries — points, lines, and polygons — with each feature linked to its municipality, district, and canton by spatial joins computed at build time.

Its attribute names are German, and the pre-trained resolver models were fine-tuned on English GeoNames descriptions, so expect to lower ``min_similarity`` and ideally to fine-tune. See :doc:`modules` and :doc:`training`.

Querying a Gazetteer
--------------------

The ``Gazetteer`` class is what resolvers use, and you can use it directly — to explore what a gazetteer contains, to check whether a place is in it before blaming the resolver, or to write a resolver of your own.

Opening a gazetteer
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

The name must correspond to an installed gazetteer. If it does not, this raises immediately with instructions rather than returning an empty gazetteer that silently finds nothing.

Searching by name
~~~~~~~~~~~~~~~~~

``search()`` finds features by name, with four methods that trade precision for recall:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

   features = gazetteer.search("Paris", method="exact")
   print(f"Found {len(features)} features")
   
   for feature in features[:5]:
       print(f"- {feature.data.get('name')}, {feature.data.get('country_name')}")

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Method
     - Behavior
   * - ``"exact"``
     - Only features whose name matches the search string exactly, ignoring case and diacritics. Fastest, and misses anything spelled differently.
   * - ``"phrase"``
     - Features whose name contains the search string as a complete phrase. Catches "New York City" when searching for "New York", but is still restrictive.
   * - ``"partial"``
     - Features whose name contains any token of the search string. Handles added or omitted articles and qualifiers, at the cost of many more candidates.
   * - ``"fuzzy"``
     - Approximate string matching, tolerating spelling variation and typos. The most permissive, and the slowest.

Two further arguments shape the result. ``tiers`` controls how many rank tiers of results to include for the non-exact methods: results are ranked by match score — BM25 relevance for phrase and partial, edit distance for fuzzy — and grouped into brackets of similar scores, so a higher value reaches further down into lower-quality matches. ``limit`` caps the number of results returned, defaulting to 10000, which matters mainly for common names under permissive methods.

.. code-block:: python

   # Only the top-ranked matches
   features = gazetteer.search("London", method="partial", tiers=1)
   
   # More permissive, including lower-ranked matches
   features = gazetteer.search("London", method="partial", tiers=3)

An empty result means either that the name is genuinely absent or that the method was too strict. Working up from ``"exact"`` through ``"fuzzy"`` is the quickest way to tell which.

Looking up by identifier
~~~~~~~~~~~~~~~~~~~~~~~~

If you know a feature's identifier, ``find()`` retrieves it directly:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

   # Paris, France, by its geonameid
   feature = gazetteer.find("2988507")
   
   if feature:
       print(f"Name: {feature.data.get('name')}")
       print(f"Country: {feature.data.get('country_name')}")
       print(f"Population: {feature.data.get('population')}")

The identifier scheme is the gazetteer's own: the geonameid for GeoNames, a UUID for SwissNames3D, and whatever you chose for a gazetteer of your own. ``find()`` returns ``None`` for an unknown identifier rather than raising, so check before using the result.

Working with Features
---------------------

``search()`` and ``find()`` return ``Feature`` objects, one per place:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")
   features = gazetteer.search("Tokyo")
   
   if features:
       feature = features[0]
       
       print(f"ID: {feature.identifier}")        # stable identifier
       print(f"Source: {feature.source}")        # which source it was built from
       print(f"Data: {feature.data}")            # attributes, as a dictionary
       print(f"Names: {feature.names}")          # every name it is searchable by
       print(f"Geometry: {feature.geometry}")    # Shapely geometry, or None
       print(f"CRS: {feature.crs}")              # e.g. EPSG:4326

The ``identifier`` is what you store to refer to this place — in annotations, in exported data, or anywhere you need the reference to survive. The ``source`` names the gazetteer source the feature came from (``allCountries`` in GeoNames), which is how you tell apart features of different kinds within one gazetteer. ``names`` holds every string the place is searchable by, unordered and unlabelled. ``data`` holds the attributes, and ``geometry`` a Shapely object in the coordinate system given by ``crs`` — usually a Point, but lines, polygons, and multi-part geometries occur too, and it is ``None`` for a place the gazetteer records by name without locating.

.. code-block:: python

   if feature.geometry is not None:
       print(feature.geometry.x, feature.geometry.y)

Attributes by gazetteer
~~~~~~~~~~~~~~~~~~~~~~~

Which keys are in ``data`` depends on the gazetteer, and on the source within it. For GeoNames:

- ``name``, ``asciiname``: The main name of the feature, and its ASCII transliteration
- ``latitude`` and ``longitude``: Coordinates in decimal degrees
- ``feature_class``: Single-letter top-level category — ``P`` populated place, ``A`` administrative area, ``H`` water, ``T`` terrain, ``S`` spot or building, ``L`` area, ``R`` road, ``U`` undersea, ``V`` vegetation. The usual way to filter results to one kind of place
- ``feature_code``, ``feature_name``: The finer-grained type code and its human-readable form ("city", "mountain", "stream")
- ``country_code``, ``country_name``: The country the feature is in
- ``admin1_name``, ``admin2_name``: First and second-level administrative divisions, with ``admin1_code`` through ``admin4_code`` for their codes
- ``population``: Population count for inhabited places
- ``elevation``, ``dem``: Elevation in metres, as recorded and as sampled from a digital elevation model
- ``cc2``, ``timezone``, ``modification_date``: Alternate country codes, timezone, and when the GeoNames record last changed

For SwissNames3D the keys vary by source, because the gazetteer is built from point, line, polygon, and boundary datasets. Present on all named features:

- ``NAME``: The name of the feature
- ``OBJEKTART``: Detailed object type, in German
- ``GEMEINDE_NAME``, ``BEZIRK_NAME``, ``KANTON_NAME``: Municipality, district, and canton, assigned by spatial join

Point features additionally carry ``HOEHE`` (elevation in metres); line features carry ``KUNSTBAUTE``, and polygon features ``EINWOHNERK`` and ``ISCED``.

Because keys differ between sources even inside one gazetteer, read them with ``feature.data.get("key")`` rather than by subscripting. The exact keys are defined per source in the gazetteer's configuration file, so a custom gazetteer has whatever keys you gave it.

Using a Gazetteer with a Resolver
---------------------------------

A resolver is told which gazetteer to use when you construct it:

.. code-block:: python

   from geoparser.modules import SentenceTransformerResolver

   resolver = SentenceTransformerResolver(gazetteer_name="swissnames3d")

For GeoNames and SwissNames3D that is all that is needed. A resolver that describes candidates in words — as ``SentenceTransformerResolver`` does — additionally has to be told which attributes to build that description from when the gazetteer is one of your own, since it cannot guess. See :doc:`modules`.

Next Steps
----------

- :doc:`custom-gazetteers` — build a gazetteer from your own data
- :doc:`modules` — how resolvers use gazetteers, and how to configure them for one of yours
