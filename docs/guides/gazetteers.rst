.. _gazetteers:

Gazetteers
==========

This guide explains how to query gazetteer data, understand feature attributes, and configure custom gazetteers for specialized geographic databases.

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

The exact data keys are defined per source in the gazetteer's configuration file.

Custom Gazetteer Configuration
-------------------------------

The library supports adding custom gazetteers through YAML configuration files. This capability allows you to integrate specialized geographic databases, regional data sources, or proprietary location data without modifying the core library code.

A configuration describes how source files *project* into the canonical feature model. It is purely declarative—there is no user-provided transformation code; the only embedded SQL allowed are small scalar expressions (string manipulation, arithmetic, ``CASE`` expressions) where a plain column reference is not enough.

Configuration Structure
~~~~~~~~~~~~~~~~~~~~~~~

A gazetteer configuration file has two top-level concepts:

.. code-block:: yaml

   name: my_gazetteer   # Unique identifier for the gazetteer
   crs: EPSG:4326       # CRS of the artifact's geometries (optional, default EPSG:4326)

   sources:             # Files to download/stage (transient; discarded after the build)
     - name: places
       # ... source configuration ...

   features:            # One block per source; each block produces features
     - source: places
       # ... feature configuration ...

``sources`` declare the source files and, explicitly, their attributes. ``features`` blocks describe how rows of one source become searchable features—their identifier, names, geometry and data—optionally enriched by ``joins`` against other sources. Sources that only serve as join targets simply aren't referenced by any feature block.

Sources
~~~~~~~

Each source is a file to acquire and stage. Sources are either **tabular** (delimited text; set ``delimiter``) or **spatial** (shapefile, GeoPackage, GeoJSON, and other GDAL-readable formats). Every source declares its ``attributes`` explicitly, and every attribute declares its ``type`` (``text``, ``integer``, ``real`` or ``geometry``), so a source's schema reads the same regardless of file format. Remote files are downloaded and cached; ZIP archives are extracted automatically, with ``file`` naming the target file inside the archive:

.. code-block:: yaml

   sources:
     - name: places
       url: https://example.com/data.zip   # Downloaded and extracted
       file: places.csv                    # File within the ZIP
       delimiter: ","
       attributes:
         - name: id
           type: integer
         - name: name
           type: text
         - name: lat
           type: real
         - name: lon
           type: real

For local files, provide a ``path`` instead of a ``url`` (relative paths are resolved against the config file's location):

.. code-block:: yaml

   sources:
     - name: local_data
       path: data/places.tsv
       file: places.tsv
       delimiter: "\t"
       quote: ""          # Disable quote handling for raw TSV files
       skip_rows: 2       # Skip leading comment lines
       attributes:
         - name: id
           type: integer
         - name: name
           type: text

A **spatial** source has no ``delimiter``. It declares its attributes the same way, including exactly one attribute of type ``geometry`` (always named ``geometry``, the name its geometry is staged under). Declare the source coordinate system with ``crs`` if it differs from the gazetteer CRS:

.. code-block:: yaml

   sources:
     - name: municipalities
       url: https://example.com/boundaries.zip
       file: municipalities.shp
       crs: EPSG:2056     # Source CRS; reprojected to the gazetteer CRS at build time
       attributes:
         - name: BFS_NUMMER
           type: integer
         - name: NAME
           type: text
         - name: geometry
           type: geometry

Feature Blocks
~~~~~~~~~~~~~~

Each ``features`` block projects one source into features. A gazetteer can define any number of blocks, each with its own set of data—there is no shared schema to pad. A block names the ``source`` it projects, and that name becomes the features' ``source`` in the artifact (so a source backs at most one block). A block is written in reading order: the ``source``, then the ``joins`` that enrich it, then the ``identifier``, ``geometry``, ``names`` and ``data`` derived from the joined rows:

.. code-block:: yaml

   features:
     - source: places         # The backing source; also the feature's source name
       identifier: "id"        # Column (or expression) with the stable identifier
       geometry: "ST_Point(lon, lat)"
       names:
         - "name"
       data:
         - "name"        # Stored under its own name
         - "population"

Column references throughout a block (in ``identifier``, ``geometry``, ``names``, ``data`` and each join's ``ON`` condition) follow one rule: a **bare** column name is a column of the block's own source, and a column of a **joined** source is referenced by qualification (``<source>.<column>``). You never need a ``src.`` prefix—bare source columns are resolved for you, even inside join clauses.

**Names** define what the feature can be found by. Each name is simply a column or scalar SQL expression—they are interchangeable, so no label distinguishes them. To register several names from one multi-value column, use an expression that splits and unnests it (each element becomes its own name):

.. code-block:: yaml

   names:
     - "name"
     - "CASE WHEN instr(name, '(') > 0 THEN trim(substr(name, 1, instr(name, '(') - 1)) ELSE name END"
     - "unnest(string_split(alternatenames, ','))"    # One name per comma-separated value

**Geometry** is a single value: a geometry column (for spatial sources) or a scalar expression that builds one (for example a point from coordinate columns). Its coordinate system is the backing source's ``crs`` (or the gazetteer CRS); geometries are reprojected to the gazetteer CRS at build time:

.. code-block:: yaml

   geometry: "geometry"                       # A geometry column of a spatial source
   # or
   geometry: "ST_Point(longitude, latitude)"  # Built from coordinate columns

**Data** lists exactly what goes into the feature's ``data`` dictionary. Each entry is a column or scalar expression, written exactly as it would appear in a SQL ``SELECT``, with an optional trailing ``AS <alias>`` naming the key it is stored under. A bare or qualified column reference (``name``, ``c.Country``) may omit the alias, in which case its own column name (the last component, for a qualified reference) is the key; a plain expression has no name of its own, so it always needs one:

.. code-block:: yaml

   data:
     - "population"                 # Bare column, stored as "population"
     - "c.Country AS country_name"  # Column of a joined source, renamed
     - "upper(name) AS name_upper"  # Expression (alias required)

Joins
~~~~~

A feature block can ``join`` other sources to enrich its rows. Each join is a **raw SQL join clause** appended to the block's source: the whole joined table becomes available (there is no separate value selection—pick what you need in ``data`` using qualified references). Within a join's ``ON`` condition, bare names are the block's source columns and joined columns are qualified (``<alias>.<column>``). Give each joined table a short alias to reference it conveniently. Joins are applied in order, so a later join can reference a table joined earlier.

An **attribute** join equates columns (or expressions) of the two sides:

.. code-block:: yaml

   joins:
     - "LEFT JOIN countryInfo c ON country_code = c.ISO"
     - "LEFT JOIN admin1CodesASCII a1 ON country_code || '.' || admin1_code = a1.code"

The joined columns are then read in ``data`` by qualification:

.. code-block:: yaml

   data:
     - "c.Country AS country_name"
     - "a1.name AS admin1_name"

A **spatial** join matches the feature geometry against the joined source's geometry with a spatial function (``ST_Within``, ``ST_Intersects``, ``ST_Contains``, ...). Reduce a geometry to its centroid inline with ``ST_Centroid`` where useful (lines and polygons):

.. code-block:: yaml

   joins:
     - "LEFT JOIN gemeinde g ON ST_Within(ST_Centroid(geometry), g.geometry)"

.. note::

   Raw joins operate on the sources' native coordinate systems and are **not** reprojected automatically, so a spatial join is only meaningful when both sides share a CRS (transform explicitly with ``ST_Transform`` otherwise). The feature's own ``geometry`` is still reprojected to the gazetteer CRS independently.

Joins can **chain**: a later join can reference a table joined earlier. This expresses multi-level hierarchies (place → municipality → district → canton):

.. code-block:: yaml

   joins:
     - "LEFT JOIN gemeinde g ON ST_Within(ST_Centroid(geometry), g.geometry)"
     - "LEFT JOIN bezirk b ON g.BEZIRKSNUM = b.BEZIRKSNUM"      # matches on the earlier join
     - "LEFT JOIN kanton k ON b.KANTONSNUM = k.KANTONSNUM"

Handling Duplicate Identifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some datasets contain multiple rows per identifier (repeated records, or multi-part geometries split across rows). Rows sharing an identifier are always **merged into a single feature**: all their names are collected, their geometries are unioned into a single (possibly multi-part) geometry, and each data value is taken from the first row of the group. This happens automatically—there is nothing to configure.

Identifiers must be unique across the entire gazetteer. If two feature blocks produce the same identifier, the build fails with a clear error; disambiguate with an expression (for example ``"'city:' || id"``) or merge the blocks.

Complete Example
~~~~~~~~~~~~~~~~

Here's a complete configuration combining a tabular place file, an attribute join, and a spatial join:

.. code-block:: yaml

   name: my_gazetteer
   crs: EPSG:4326

   sources:
     - name: places
       url: https://example.com/places.zip
       file: places.csv
       delimiter: ","
       attributes:
         - name: id
           type: integer
         - name: name
           type: text
         - name: alt_names
           type: text
         - name: region_code
           type: text
         - name: lat
           type: real
         - name: lon
           type: real

     - name: regions
       url: https://example.com/regions.csv
       file: regions.csv
       delimiter: ","
       attributes:
         - name: code
           type: text
         - name: label
           type: text

     - name: protected_areas
       url: https://example.com/areas.zip
       file: areas.shp
       crs: EPSG:3857
       attributes:
         - name: AREA_NAME
           type: text
         - name: geometry
           type: geometry

   features:
     - source: places
       joins:
         - "LEFT JOIN regions r ON region_code = r.code"
         - "LEFT JOIN protected_areas a ON ST_Within(ST_Point(lon, lat), ST_Transform(a.geometry, 'EPSG:3857', 'EPSG:4326', always_xy := true))"
       identifier: "id"
       geometry: "ST_Point(lon, lat)"
       names:
         - "name"
         - "unnest(string_split(alt_names, ','))"
       data:
         - "name"
         - "r.label AS region_name"
         - "a.AREA_NAME AS protected_area"

For real-world examples, refer to the built-in gazetteer configurations on GitHub: `geonames.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames.yaml>`_, `geonames-cities.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames-cities.yaml>`_ (multiple feature blocks), and `swissnames3d.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/swissnames3d.yaml>`_ (spatial joins, duplicate-identifier merging).

Installing Custom Gazetteers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install a custom gazetteer, provide the path to your configuration file:

.. code-block:: bash

   python -m geoparser install path/to/my_gazetteer.yaml

The build validates the configuration, downloads or locates the specified files, stages them, runs the projections, and writes the finished artifact. If anything is wrong with the configuration—an unknown column, an invalid join clause, colliding identifiers—the build stops with a descriptive error and nothing is installed. A successful build atomically replaces any previously installed artifact of the same name.

.. note::
   Building gazetteers with geometries requires DuckDB's spatial extension, which is downloaded automatically on first use. If you build gazetteers in an offline environment, run one spatial build while online first so the extension is cached.

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.
