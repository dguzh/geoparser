.. _gazetteers:

Working with Gazetteers
=======================

Gazetteers are geographic databases that store information about places, including their names, types, administrative hierarchies, and coordinates. The Irchel Geoparser uses gazetteers as the knowledge source for resolving place names to specific locations. Understanding how gazetteers work and how to query them is essential for working with resolvers and for configuring custom geographic databases.

Understanding Gazetteers
------------------------

A gazetteer serves as the authoritative source of geographic information that resolvers consult when disambiguating place names. When you mention "Paris" in a text, the gazetteer contains entries for Paris, France; Paris, Texas; Paris, Ontario; and many other places named Paris around the world. Each entry includes not just the name but also attributes like coordinates, population, feature type, and administrative hierarchy that help distinguish one Paris from another.

The library's architecture separates the gazetteer system from the processing modules. Resolvers don't access gazetteers directly through SQL queries or file reads—instead, they use the ``Gazetteer`` class interface which provides standardized search methods. This abstraction allows gazetteers to have different internal schemas and still be used interchangeably by resolvers.

Gazetteers in the library are stored in a centralized SQLite database that includes spatial indexing capabilities through the SpatiaLite extension. This database can contain multiple gazetteers simultaneously, each with its own tables and indices. The gazetteer installer handles all the complexity of downloading source data, transforming it into the right format, creating database schemas, and building indices.

Built-in Gazetteers
-------------------

The library includes support for two major gazetteers that cover different geographic scopes and use cases.

GeoNames
~~~~~~~~

GeoNames is a comprehensive global gazetteer containing over 13 million place names. It includes entries for countries, administrative divisions, cities, towns, neighborhoods, natural features like mountains and rivers, and points of interest like buildings and monuments. GeoNames provides standardized codes for feature types (e.g., PPL for populated place, HLL for hill, STM for stream) and maintains hierarchical relationships between places through administrative codes.

The GeoNames data includes population figures for inhabited places, elevation values for many features, and alternate names in multiple languages and writing systems. This rich attribute set makes GeoNames suitable for a wide range of applications, from news article geoparsing to social media analysis to historical text processing. However, the global scope means that coverage varies significantly by region, with some areas having more detailed and up-to-date information than others.

To install GeoNames:

.. code-block:: bash

   python -m geoparser download geonames

The installation process downloads several files totaling about 1.7 GB compressed, which expand to approximately 3.3 GB in the database. The process includes creating spatial indices and processing alternate names, which can take 15-30 minutes depending on your system.

SwissNames3D
~~~~~~~~~~~~

SwissNames3D is a high-quality gazetteer specifically for Switzerland, provided by Swisstopo, the Swiss Federal Office of Topography. It contains detailed information about geographic features within Switzerland, including precise 3D coordinates, building addresses, and fine-grained feature classifications. The gazetteer is maintained by professional cartographers and updated regularly, making it one of the most accurate and complete geographic databases available for any country.

SwissNames3D includes not just major cities but also small neighborhoods, individual streets, buildings, bridges, peaks, valleys, and other landscape features. Each entry is classified according to a detailed schema that distinguishes between different types of settlements, infrastructure, terrain, and vegetation. The gazetteer also maintains relationships with administrative boundaries, allowing features to be associated with municipalities, districts, and cantons.

For applications focused on Switzerland, SwissNames3D provides significantly better results than GeoNames because of its comprehensive coverage, precise coordinates, and detailed feature classifications. The trade-off is that it only covers Switzerland—it won't help resolve place names in other countries.

To install SwissNames3D:

.. code-block:: bash

   python -m geoparser download swissnames3d

The installation downloads about 120 MB compressed, expanding to approximately 200 MB in the database. The process typically completes within a few minutes.

Querying Gazetteers
-------------------

The ``Gazetteer`` class provides a Python interface for querying gazetteer data. This interface is primarily used by resolvers, but you can also use it directly for exploration or custom processing logic.

Initializing a Gazetteer
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a gazetteer instance by specifying its name:

.. code-block:: python

   from geoparser.gazetteer import Gazetteer

   gazetteer = Gazetteer("geonames")

The gazetteer name must correspond to an installed gazetteer in the database. If the gazetteer isn't installed, an error will occur when you try to query it.

Searching for Features
~~~~~~~~~~~~~~~~~~~~~~

The ``search()`` method finds features matching a given name string. It supports different search methods that trade off precision and recall:

.. code-block:: python

   from geoparser.gazetteer import Gazetteer

   gazetteer = Gazetteer("geonames")

   # Exact string matching
   features = gazetteer.search("Paris", method="exact")
   print(f"Found {len(features)} features")
   
   for feature in features[:5]:  # Show first 5
       print(f"- {feature.data.get('name')}, {feature.data.get('country_name')}")

The search method parameter controls the matching strategy:

- ``"exact"``: Only returns features whose name exactly matches the search string (case-insensitive). This is the fastest method but will miss features with slightly different names.

- ``"phrase"``: Returns features whose name contains the search string as a complete phrase. This catches variations like "New York City" when searching for "New York" but is still quite restrictive.

- ``"partial"``: Returns features whose name contains any of the tokens in the search string. This is more flexible and can handle cases where articles or qualifiers are included or omitted, but it may return many candidates.

- ``"fuzzy"``: Uses fuzzy string matching to find features with names similar to the search string, even with spelling variations or typos. This is the most permissive method and generates the most candidates.

The ``limit`` parameter controls the maximum number of results returned:

.. code-block:: python

   # Get up to 100 matching features
   features = gazetteer.search("Springfield", method="partial", limit=100)

For the non-exact search methods, you can also specify a ``tiers`` parameter that controls how many rank tiers of results to include. Results are ranked by a combination of string similarity and feature importance (like population), and tiers group results into brackets of similar rank. Higher tier values include more results but also results with lower match quality:

.. code-block:: python

   # Get only the top-ranked matches
   features = gazetteer.search("London", method="partial", tiers=1)
   
   # Get more permissive results including lower-ranked matches
   features = gazetteer.search("London", method="partial", tiers=3)

Finding Features by Identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you know a feature's identifier, you can retrieve it directly using the ``find()`` method:

.. code-block:: python

   from geoparser.gazetteer import Gazetteer

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

   from geoparser.gazetteer import Gazetteer

   gazetteer = Gazetteer("geonames")
   features = gazetteer.search("Tokyo")
   
   if features:
       feature = features[0]
       
       # The feature's unique identifier value
       print(f"ID: {feature.location_id_value}")
       
       # The feature's attributes as a dictionary
       print(f"Data: {feature.data}")

The ``location_id_value`` property contains the identifier that can be used to reference this feature, for example when creating referent annotations. The ``data`` property is a dictionary containing all the attributes from the gazetteer for this feature.

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

The library supports adding custom gazetteers through YAML configuration files. This capability allows you to integrate specialized geographic databases, regional data sources, or proprietary location data without modifying the core library code.

A gazetteer configuration file describes the data sources (files to download or local files to use), their format (tabular like CSV/TSV or spatial like shapefiles), the attributes to extract from each source, how to transform and derive new attributes, how to join multiple sources together into a unified view, and which attributes identify features and provide their names.

Here's a simplified example of a configuration structure:

.. code-block:: yaml

   name: my_gazetteer
   sources:
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
           - name: place_name
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
       features:
         identifier:
           - column: id
         names:
           - column: place_name

The configuration specifies that this gazetteer has a source called "places" that should be downloaded from a URL and parsed as a comma-separated CSV file. The source has four original attributes (id, place_name, lat, lon) and one derived attribute (geometry) computed from an SQL expression. The configuration marks id and geometry for indexing to speed up queries. Finally, it specifies that features are identified by the id column and named by the place_name column.

More complex configurations can include multiple sources that are joined together (like GeoNames joining place data with administrative hierarchy data), attributes that should be dropped from the final view, spatial queries for determining administrative containment, and multiple name columns including fields that contain delimiter-separated lists of alternate names.

The complete configuration schema is quite extensive and allows for sophisticated transformations and queries. The built-in gazetteer configurations (``geoparser/gazetteer/configs/geonames.yaml`` and ``geoparser/gazetteer/configs/swissnames3d.yaml``) serve as comprehensive examples that demonstrate the full capabilities of the configuration system.

To install a custom gazetteer, provide the path to your configuration file to the installation command:

.. code-block:: bash

   python -m geoparser download path/to/my_gazetteer.yaml

The installer validates the configuration, downloads or locates the specified files, creates database tables according to the attribute specifications, loads the data, applies transformations and derivations, creates indices, and registers the gazetteer so it can be queried through the standard interface.

Gazetteer Installer Architecture
---------------------------------

The gazetteer installer orchestrates a multi-stage pipeline that transforms raw geographic data into an optimized, queryable database. The pipeline consists of six stages: acquisition (downloading and extracting files), schema creation (building database tables), ingestion (loading raw data), transformation (applying derivations and building geometries), indexing (creating database indices), and registration (storing feature identifiers and names in searchable tables).

Each stage is designed to be independent and testable, with well-defined inputs and outputs. The acquisition stage handles different source types (local files, HTTP downloads, ZIP archives) transparently. The schema stage generates SQL table definitions from the configuration's attribute specifications, including proper type mappings and foreign key relationships. The ingestion stage uses efficient bulk loading strategies and processes data in chunks to handle large files. The transformation stage executes SQL expressions to compute derived attributes, with special handling for geometry construction. The indexing stage creates both standard B-tree indices and spatial R-tree indices. The registration stage populates the search tables that support the different search methods.

This architecture means that adding support for a new gazetteer is primarily a data modeling exercise rather than a programming task. You describe the gazetteer's structure and relationships in YAML, and the installer handles the technical details of database creation and optimization.

Best Practices
--------------

When working with gazetteers, several practices help ensure good results and efficient processing. Choose the gazetteer that best matches your application's geographic scope. If you're processing texts about a specific region, a regional gazetteer typically provides better coverage and accuracy than a global one. If you need global coverage, GeoNames is the standard choice, but be aware that its quality and completeness vary significantly by country.

When querying gazetteers in resolvers, start with restrictive search methods (exact or phrase) and only fall back to more permissive methods (partial or fuzzy) if necessary. This strategy keeps candidate lists manageable and reduces false positives. The ``SentenceTransformerResolver`` implements this iterative strategy automatically, but if you're writing custom resolvers, consider adopting a similar approach.

Be mindful of the computational cost of different operations. Fuzzy search is significantly slower than exact search, and increasing the limit or tiers parameters can substantially increase both search time and the number of candidates that need to be processed. Set these parameters based on your performance requirements and the characteristics of your data.

When developing custom gazetteers, invest time in the configuration design. Think carefully about which attributes are essential versus nice-to-have, as each attribute adds to database size and query complexity. Create indices on attributes that will be used in search queries or join conditions, but avoid creating indices unnecessarily as they slow down data loading and increase storage requirements.

For gazetteers with hierarchical administrative structures, consider whether you need to store this information redundantly in each feature's record (which speeds up queries but increases storage) or keep it normalized in separate tables (which saves space but requires joins). The built-in gazetteers use a mixed approach, storing administrative codes in feature records and full names in joined tables.

Test your gazetteer configuration with a small subset of data before running a full installation. This allows you to catch configuration errors quickly without waiting through a long installation process. The installer will fail fast if it encounters problems, but catching them early saves time.

If you're building a gazetteer from multiple sources, carefully consider the join conditions and administrative relationships. Spatial joins (like "which municipality contains this feature") can be expensive but provide accurate results. Attribute-based joins (like matching administrative codes) are faster but require that the codes are consistent across sources. The configuration supports both approaches.

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`working_with_projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.

