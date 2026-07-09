.. _gazetteers:

Gazetteers
==========

This guide explains how to query gazetteer data, understand feature attributes, and configure custom gazetteers for specialized geographic databases.

Overview
--------

The Irchel Geoparser uses gazetteers as the authoritative source of geographic information for toponym resolution. A gazetteer stores information about places, including their names, types, administrative hierarchies, and coordinates. When you mention "Paris" in a text, the gazetteer contains entries for Paris, France; Paris, Texas; Paris, Ontario; and many other places named Paris around the world. Each entry includes not just the name but also attributes like coordinates, population, feature type, and administrative hierarchy that help distinguish one Paris from another.

The library's architecture separates the gazetteer system from the processing modules. Resolvers don't access gazetteers directly through SQL queries or file reads—instead, they use the ``Gazetteer`` class interface which provides standardized search methods.

Every installed gazetteer is a single, self-contained SQLite file (an *artifact*) with a fixed schema shared by all gazetteers: a ``feature`` table (identifier, entity type, attributes as JSON, geometry as WKB), a ``name`` table with full-text and phonetic indexes for search, and a small ``metadata`` table. Artifacts are built from declarative YAML configurations by a build pipeline that downloads the source files, stages them in a transient analytical database (DuckDB), and projects them into the canonical schema—including joins, spatial joins, and deduplication. The source files and staging data are discarded after the build; the artifact is the only thing installed, and it is never modified afterwards.

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
       
       # The feature's entity type
       print(f"Type: {feature.type}")
       
       # The feature's attributes as a dictionary
       print(f"Data: {feature.data}")
       
       # The feature's searchable names
       print(f"Names: {feature.names}")
       
       # The feature's geometry as a Shapely object
       print(f"Geometry: {feature.geometry}")
       print(f"Coordinates: ({feature.geometry.x}, {feature.geometry.y})")

The ``identifier`` property contains the identifier that can be used to reference this feature, for example when creating referent annotations. The ``type`` property names the feature's entity type as defined by the gazetteer configuration (for example ``place`` in GeoNames, or ``city`` / ``country`` / ``admin1`` in GeoNames Cities). The ``data`` property is a dictionary containing all the attributes stored for this feature; different entity types can have entirely different attribute sets. The ``geometry`` property returns a Shapely geometry object in the gazetteer's coordinate reference system (available as ``feature.crs``). Most gazetteers use Point geometries for locations, but this can also be lines, polygons, or multi-part geometries depending on the gazetteer.

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

The exact attributes are defined per entity type in the gazetteer's configuration file.

Custom Gazetteer Configuration
-------------------------------

The library supports adding custom gazetteers through YAML configuration files. This capability allows you to integrate specialized geographic databases, regional data sources, or proprietary location data without modifying the core library code.

A configuration describes how source files *project* into the canonical feature model. It is purely declarative—there is no user-provided transformation code; the only embedded SQL allowed are small scalar expressions (string manipulation, arithmetic, ``CASE`` expressions) where a plain column reference is not enough.

Configuration Structure
~~~~~~~~~~~~~~~~~~~~~~~

A gazetteer configuration file has three top-level concepts:

.. code-block:: yaml

   name: my_gazetteer   # Unique identifier for the gazetteer
   crs: EPSG:4326       # CRS of the artifact's geometries (optional, default EPSG:4326)

   inputs:              # Files to download/stage (transient; discarded after the build)
     - name: places
       # ... input configuration ...

   lookups:             # Named, reusable enrichments (joins against other inputs)
     country:
       # ... lookup configuration ...

   features:            # One block per entity type; each block produces features
     - type: place
       # ... feature configuration ...

``inputs`` declare the source files. ``lookups`` define reusable many-to-one joins that enrich feature rows with values from other inputs (like administrative names). ``features`` blocks describe how rows of an input become searchable features—their identifier, names, geometry, and attributes. Inputs that only serve as join targets simply aren't referenced by any feature block.

Inputs
~~~~~~

Each input is a file to acquire and stage. Inputs are either **tabular** (delimited text; set ``delimiter``) or **spatial** (shapefile, GeoPackage, GeoJSON, and other GDAL-readable formats). Remote files are downloaded and cached; ZIP archives are extracted automatically, with ``file`` naming the target file inside the archive:

.. code-block:: yaml

   inputs:
     - name: places
       url: https://example.com/data.zip   # Downloaded and extracted
       file: places.csv                    # File within the ZIP
       delimiter: ","
       columns:                            # For headerless files: declare the columns
         - { name: id, type: integer }
         - { name: name }                  # type defaults to text
         - { name: lat, type: real }
         - { name: lon, type: real }

For local files, provide a ``path`` instead of a ``url`` (relative paths are resolved against the config file's location):

.. code-block:: yaml

   inputs:
     - name: local_data
       path: data/places.tsv
       file: places.tsv
       delimiter: "\t"
       quote: ""          # Disable quote handling for raw TSV files
       skip_rows: 2       # Skip leading comment lines

Spatial inputs need no ``delimiter`` or ``columns``—their schema comes from the file itself, and their geometry is always exposed under the column name ``geometry``. Declare the source coordinate system with ``crs`` if it differs from the gazetteer CRS:

.. code-block:: yaml

   inputs:
     - name: municipalities
       url: https://example.com/boundaries.zip
       file: municipalities.shp
       crs: EPSG:2056     # Source CRS; reprojected to the gazetteer CRS at build time

Lookups
~~~~~~~

Lookups are named, reusable enrichments: a lookup left-joins feature rows against another input and exposes selected columns under new names. Define a lookup once and reference it from any number of feature blocks.

An **attribute lookup** matches on column equality. The left side of each ``on`` pair is a column of the feature's input (or a scalar expression over its columns); the right side is a column of the lookup input:

.. code-block:: yaml

   lookups:
     country:
       from: countryInfo
       match: { on: { country_code: ISO } }
       values: { country_name: Country }      # exposes "country_name"

     admin1:
       from: admin1CodesASCII
       match: { on: { "country_code || '.' || admin1_code": code } }   # expression key
       values: { admin1_name: name }

A **spatial lookup** matches the feature's geometry against the lookup input's geometry. The supported predicates are ``within``, ``intersects``, and ``contains``; ``using: centroid`` reduces the feature geometry to its centroid before matching (useful for lines and polygons). Coordinate systems are aligned automatically:

.. code-block:: yaml

   lookups:
     in_gemeinde:
       from: gemeinde
       match: { spatial: within, using: centroid }
       values: { GEMEINDE_NAME: NAME, BEZIRKSNUM: BEZIRKSNUM }

Lookups can **chain**: a later lookup can match on a value exposed by an earlier one. This expresses multi-level hierarchies (place → municipality → district → canton) without repeating join logic:

.. code-block:: yaml

   lookups:
     in_bezirk:
       from: bezirk
       match: { on: { BEZIRKSNUM: BEZIRKSNUM } }   # BEZIRKSNUM comes from in_gemeinde
       values: { BEZIRK_NAME: NAME, KANTONSNUM: KANTONSNUM }

Feature Blocks
~~~~~~~~~~~~~~

Each ``features`` block projects one input into features of one entity type. A gazetteer can define any number of entity types, each with its own attribute set—there is no shared schema to pad:

.. code-block:: yaml

   features:
     - type: place
       from: places            # The input providing the rows
       identifier: id          # Column (or expression) with the stable identifier
       names:
         - column: name
       geometry:
         point: { lon: lon, lat: lat }
       lookups: [country, admin1]
       attributes:
         - name                # Shorthand: attribute "name" from column "name"
         - population
         - country_name        # Values exposed by lookups work like columns
         - admin1_name

**Names** define what the feature can be found by. A feature can have any number of names, from its own columns, from expressions, from multi-value columns (``split``), or from a separate one-to-many names table (``from``/``key``):

.. code-block:: yaml

   names:
     - column: name
     - expression: "CASE WHEN instr(name, '(') > 0 THEN trim(substr(name, 1, instr(name, '(') - 1)) ELSE name END"
     - column: alternatenames
       split: ","                        # One name per comma-separated value
     - from: alternate_names             # A related input with one name per row
       key: place_id                     # Column of that input holding the feature identifier
       column: alternate_name

**Geometry** is either a geometry ``column`` (for spatial inputs) or a ``point`` built from coordinate columns. A per-feature ``crs`` declares the coordinate system of the source values; geometries are reprojected to the gazetteer CRS at build time:

.. code-block:: yaml

   geometry: { column: geometry, crs: EPSG:2056 }
   # or
   geometry: { point: { lon: longitude, lat: latitude } }

**Attributes** list exactly what goes into the feature's ``data`` dictionary. Each entry is a column name (string shorthand), a renamed column, or a scalar expression:

.. code-block:: yaml

   attributes:
     - population
     - { name: KANTON_NAME, column: NAME }         # Renamed
     - { name: name_upper, expression: "upper(name)" }

Handling Duplicate Identifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some datasets contain multiple rows per identifier (repeated records, or multi-part geometries split across rows). Rows sharing an identifier are always **merged into a single feature**, under an explicit, configurable policy:

.. code-block:: yaml

   features:
     - type: named_area
       from: ply
       identifier: UUID
       merge:
         geometry: union        # first (default) | union: combine into a multi-part geometry
         attributes: first      # first (default) | min | max: block-wide default
       names:
         - column: NAME         # Names are always collected across duplicate rows
       attributes:
         - OBJEKTART
         - { name: EINWOHNERK, merge: max }   # Per-attribute override

Names are always collected across all duplicate rows. Geometries either keep the first row's geometry or are unioned into a multi-part geometry. Attribute values keep the first row's value by default, with ``min``/``max`` available per attribute or as a block-wide default.

Identifiers must be unique across the entire gazetteer. If two feature blocks produce the same identifier, the build fails with a clear error; disambiguate with an expression (for example ``"'city:' || id"``) or merge the blocks.

Complete Example
~~~~~~~~~~~~~~~~

Here's a complete configuration combining a tabular place file, an attribute lookup, and a spatial lookup:

.. code-block:: yaml

   name: my_gazetteer
   crs: EPSG:4326

   inputs:
     - name: places
       url: https://example.com/places.zip
       file: places.csv
       delimiter: ","
       columns:
         - { name: id, type: integer }
         - { name: name }
         - { name: alt_names }
         - { name: region_code }
         - { name: lat, type: real }
         - { name: lon, type: real }

     - name: regions
       url: https://example.com/regions.csv
       file: regions.csv
       delimiter: ","
       columns:
         - { name: code }
         - { name: label }

     - name: protected_areas
       url: https://example.com/areas.zip
       file: areas.shp
       crs: EPSG:3857

   lookups:
     region:
       from: regions
       match: { on: { region_code: code } }
       values: { region_name: label }
     protected:
       from: protected_areas
       match: { spatial: within }
       values: { protected_area: AREA_NAME }

   features:
     - type: place
       from: places
       identifier: id
       names:
         - column: name
         - column: alt_names
           split: ","
       geometry:
         point: { lon: lon, lat: lat }
       lookups: [region, protected]
       attributes:
         - name
         - region_name
         - protected_area

For real-world examples, refer to the built-in gazetteer configurations on GitHub: `geonames.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames.yaml>`_, `geonames-cities.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames-cities.yaml>`_ (multiple entity types), and `swissnames3d.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/swissnames3d.yaml>`_ (spatial lookups, duplicate-identifier merging).

Installing Custom Gazetteers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install a custom gazetteer, provide the path to your configuration file:

.. code-block:: bash

   python -m geoparser install path/to/my_gazetteer.yaml

The build validates the configuration, downloads or locates the specified files, stages them, runs the projections, and writes the finished artifact. If anything is wrong with the configuration—an unknown column, a broken lookup reference, colliding identifiers—the build stops with a descriptive error and nothing is installed. A successful build atomically replaces any previously installed artifact of the same name.

.. note::
   Building gazetteers with geometries requires DuckDB's spatial extension, which is downloaded automatically on first use. If you build gazetteers in an offline environment, run one spatial build while online first so the extension is cached.

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.
