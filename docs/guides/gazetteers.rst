.. _gazetteers:

Gazetteers
==========

This guide explains how to query gazetteer data, understand feature attributes, and configure custom gazetteers for specialized geographic databases.

Overview
--------

The Irchel Geoparser uses gazetteers as the authoritative source of geographic information for toponym resolution. A gazetteer stores information about places, including their names, types, administrative hierarchies, and coordinates. When you mention "Paris" in a text, the gazetteer contains entries for Paris, France; Paris, Texas; Paris, Ontario; and many other places named Paris around the world. Each entry includes not just the name but also attributes like coordinates, population, feature type, and administrative hierarchy that help distinguish one Paris from another.

The library's architecture separates the gazetteer system from the processing modules. Resolvers don't access gazetteers directly through SQL queries or file reads—instead, they use the ``Gazetteer`` class interface which provides standardized search methods. This abstraction allows gazetteers to have different internal schemas and still be used interchangeably by resolvers.

Gazetteers are stored in a centralized SQLite database that includes spatial indexing capabilities through the SpatiaLite extension. This database can contain multiple gazetteers simultaneously, each with its own tables and indices. The gazetteer installer handles all the complexity of downloading source data, transforming it into the right format, creating database schemas, and building indices.

Built-in Gazetteers
-------------------

The library includes support for two major gazetteers that cover different geographic scopes and use cases.

GeoNames
~~~~~~~~

GeoNames is a comprehensive global gazetteer containing over 13 million place names. It includes entries for countries, administrative divisions, cities, towns, neighborhoods, natural features like mountains and rivers, and points of interest like buildings and monuments. However, the global scope means that coverage varies significantly by region, with some areas having more detailed and up-to-date information than others.

To install GeoNames:

.. code-block:: bash

   python -m geoparser download geonames

The installation process can take up to 15-30 minutes depending on your system.

SwissNames3D
~~~~~~~~~~~~

SwissNames3D is a high-quality gazetteer specifically for Switzerland, provided by Swisstopo, the Swiss Federal Office of Topography. It contains detailed information about geographic features within Switzerland, including precise 3D coordinates, building addresses, and fine-grained feature classifications. The gazetteer also maintains relationships with administrative boundaries, allowing features to be associated with municipalities, districts, and cantons.

To install SwissNames3D:

.. code-block:: bash

   python -m geoparser download swissnames3d

The installation process typically completes within a few minutes.

Querying Gazetteers
-------------------

The ``Gazetteer`` class provides a Python interface for querying gazetteer data. This interface is primarily used by resolvers, but you can also use it directly for exploration or custom processing logic.

Initializing a Gazetteer
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a gazetteer instance by specifying its name:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("geonames")

The gazetteer name must correspond to an installed gazetteer in the database. If the gazetteer isn't installed, an error will occur when you try to query it.

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

For the non-exact search methods, you can specify a ``tiers`` parameter that controls how many rank tiers of results to include. Results are ranked by their match score (BM25 relevance for phrase/partial methods, edit distance for fuzzy method), and tiers group results into brackets of similar scores. Higher tier values include more results but also results with lower match quality:

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
       
       # The feature's unique identifier value
       print(f"ID: {feature.location_id_value}")
       
       # The feature's attributes as a dictionary
       print(f"Data: {feature.data}")
       
       # The feature's geometry as a Shapely object
       print(f"Geometry: {feature.geometry}")
       print(f"Coordinates: ({feature.geometry.x}, {feature.geometry.y})")

The ``location_id_value`` property contains the identifier that can be used to reference this feature, for example when creating referent annotations. The ``data`` property is a dictionary containing all the attributes from the gazetteer for this feature. The ``geometry`` property returns a Shapely geometry object representing the feature's spatial extent. Most gazetteers use Point geometries for locations, but this can also be polygons or other geometry types depending on the gazetteer.

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

The exact attribute schema is defined in the gazetteer's configuration file and reflected in the database schema.

Custom Gazetteer Configuration
-------------------------------

The library supports adding custom gazetteers through YAML configuration files. This capability allows you to integrate specialized geographic databases, regional data sources, or proprietary location data without modifying the core library code. A gazetteer configuration describes data sources, their formats, how to process and transform the data, and how features should be identified and named.

Configuration Structure
~~~~~~~~~~~~~~~~~~~~~~~

A gazetteer configuration file has the following top-level structure:

.. code-block:: yaml

   name: my_gazetteer  # Unique identifier for the gazetteer
   sources:            # List of data sources to process
     - name: source1
       # ... source configuration ...
     - name: source2
       # ... source configuration ...

Each source describes a single data file or download that will be loaded into the database. Sources can be combined through joins to create a unified view of geographic features. Not all sources need to provide features directly—some sources can serve as auxiliary data that enrich other sources through joins (such as administrative boundary data or alternate name lookups).

Source Types and Downloads
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sources can be either tabular (CSV, TSV) or spatial (shapefiles, GeoPackage). For tabular sources, specify the separator character. For URLs, the installer automatically handles ZIP archives:

.. code-block:: yaml

   sources:
     - name: places
       url: https://example.com/data.zip  # Downloaded and extracted
       file: places.csv                   # File within the ZIP
       type: tabular
       separator: ","

For local files, provide both the ``path`` (directory containing the file) and ``file`` (filename):

.. code-block:: yaml

   sources:
     - name: local_data
       path: /path/to/data/directory
       file: data.csv
       type: tabular
       separator: "\t"

Defining Attributes
~~~~~~~~~~~~~~~~~~~

Each source must declare its attributes in two categories: original attributes that exist in the source file, and derived attributes computed from SQL expressions.

Original attributes match columns in the source file. Specify their data types (TEXT, INTEGER, REAL, GEOMETRY) and optionally mark them for indexing:

.. code-block:: yaml

   attributes:
     original:
       - name: geonameid
         type: INTEGER
         index: true         # Create database index
       - name: name
         type: TEXT
       - name: latitude
         type: REAL
       - name: longitude
         type: REAL
       - name: population
         type: INTEGER

Derived attributes are computed using SQL expressions. This is useful for constructing geometries from coordinates, concatenating fields, or applying transformations:

.. code-block:: yaml

   attributes:
     derived:
       - name: geometry
         type: GEOMETRY
         expression: "'POINT(' || longitude || ' ' || latitude || ')'"
         index: true
         srid: 4326           # Spatial reference system
       - name: full_code
         type: TEXT
         expression: "country_code || '.' || admin_code"
         index: true
       - name: name_normalized
         type: TEXT
         expression: "lower(trim(name))"

Creating Views with Joins
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have multiple sources, you need to define a view that specifies which columns to include in the final gazetteer and how to join the sources together. The view section lists the columns to select and the join conditions:

.. code-block:: yaml

   view:
     select:
       - source: places        # Source table name
         column: geonameid     # Column to include
       - source: places
         column: name
       - source: places
         column: latitude
       - source: places
         column: longitude
       - source: admin_names   # From a different source
         column: name
         alias: admin_name     # Rename column in view
       - source: places
         column: geometry
     join:
       - type: LEFT JOIN       # Join type
         source: admin_names   # Source to join
         condition: places.admin_code = admin_names.code  # Join condition

You can use any SQL join type (LEFT JOIN, INNER JOIN, etc.) and specify complex join conditions. This allows you to enrich your main features table with data from auxiliary tables.

Spatial Joins
~~~~~~~~~~~~~

For determining spatial relationships (e.g., which administrative region contains each feature), you can use spatial join conditions with SpatiaLite functions:

.. code-block:: yaml

   join:
     - type: LEFT JOIN
       source: municipalities
       condition: ST_Within(places.geometry, municipalities.geometry)

This joins each place with the municipality whose boundary contains it. Note that spatial joins can be computationally expensive for large datasets.

Defining Features
~~~~~~~~~~~~~~~~~

The final step is specifying how features are identified and named. The identifier column(s) provide unique IDs for features, while name columns define searchable names:

.. code-block:: yaml

   features:
     identifier:
       - column: geonameid     # Primary identifier column
     names:
       - column: name          # Main name
       - column: asciiname     # ASCII variant
       - column: alternatenames  # Multiple names in one column
         separator: ","        # Split on commas

Name columns with separators are split into individual names during registration, allowing a single feature to be found under multiple name variants.

Complete Example
~~~~~~~~~~~~~~~~

Here's a complete configuration demonstrating both tabular and spatial sources combined with a spatial join:

.. code-block:: yaml

   name: my_gazetteer
   sources:
     # Main tabular source with point locations and view
     - name: places
       url: https://example.com/places.csv
       file: places.csv
       type: tabular
       separator: ","
       attributes:
         original:
           - name: id
             type: INTEGER
             index: true
           - name: name
             type: TEXT
           - name: lat
             type: REAL
           - name: lon
             type: REAL
         derived:
           - name: geometry
             type: GEOMETRY
             expression: "'POINT(' || lon || ' ' || lat || ')'"
             index: true
             srid: 4326
       view:
         select:
           - source: places
             column: id
           - source: places
             column: name
           - source: places
             column: lat
           - source: places
             column: lon
           - source: regions
             column: region_name
           - source: places
             column: geometry
         join:
           - type: LEFT JOIN
             source: regions
             condition: ST_Within(places.geometry, regions.geometry)
       features:
         identifier:
           - column: id
         names:
           - column: name
     
     # Auxiliary spatial source with administrative boundaries
     - name: regions
       url: https://example.com/regions.zip
       file: regions.shp
       type: spatial
       attributes:
         original:
           - name: region_id
             type: INTEGER
           - name: region_name
             type: TEXT
           - name: geometry
             type: GEOMETRY
             index: true
             srid: 4326

This example shows how tabular place data can be enriched with regional information from a spatial data source through a spatial join. The view is defined on the source that provides features (places), while the regions source serves as auxiliary data. For more comprehensive examples, refer to the built-in gazetteer configurations on GitHub: `geonames.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames.yaml>`_ and `swissnames3d.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/swissnames3d.yaml>`_.

Installing Custom Gazetteers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install a custom gazetteer, provide the path to your configuration file:

.. code-block:: bash

   python -m geoparser download path/to/my_gazetteer.yaml

The installer validates the configuration, downloads or locates the specified files, creates database tables according to the attribute specifications, loads the data, applies transformations and derivations, creates indices, and registers the gazetteer so it can be queried through the standard interface.

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.

