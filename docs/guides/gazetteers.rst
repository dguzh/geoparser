.. _gazetteers:

Gazetteers
==========

This guide explains what a gazetteer is in this library, which ones ship with it, and how to query them. Its second half, :ref:`custom-gazetteers`, works through building one from your own data.

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

.. _custom-gazetteers:

Custom Gazetteers
-----------------

The gazetteers above cover the modern world and one country in detail, but no fixed set of gazetteers can cover every research question. If you work on a region, a period, or a domain that is not represented — a national placename register, an excavation catalogue, a historical map index, your own field data — you can turn that data into a gazetteer of your own, and everything described so far in this guide then treats it exactly like a built-in one.

You do this by writing a YAML configuration file that describes your source files and how their rows map onto places. There is no plugin to write and no code to run: you declare where the files are, what columns they have, and which of those columns are the identifier, the names, the geometry, and the attributes of a place. The build pipeline does the rest.

The rest of this guide walks through that process end to end on a real dataset, then documents every configuration key in full.

What You Are Building
~~~~~~~~~~~~~~~~~~~~~

Before writing any configuration, it helps to know exactly what the build produces, because that is what your configuration has to describe.

The Canonical Feature Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every gazetteer, however heterogeneous its sources, is projected into a single model. A gazetteer is a set of **features**, and each feature has exactly five things:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Field
     - Meaning
   * - ``identifier``
     - A string that identifies the place within this gazetteer and never changes. It is what gets stored in annotations, so it must be stable across rebuilds and unique across the whole gazetteer.
   * - ``names``
     - Every string the place should be findable by: its main name, historical spellings, transliterations, names in other languages, abbreviations. Names are not ranked or labelled — they are a set of search keys.
   * - ``geometry``
     - One geometry (point, line, polygon, or a multi-part combination), in the gazetteer's coordinate reference system. It may be absent: a place that is known by name but not located is still a perfectly valid feature.
   * - ``data``
     - A free-form dictionary of attributes: type, hierarchy, population, dates, links, descriptions — whatever your source offers and your work needs. There is no fixed schema, and different sources within one gazetteer may store entirely different keys.
   * - ``source``
     - Which of the configuration's sources the feature came from. Set automatically; useful for telling apart features of different kinds in one gazetteer.

The finished gazetteer is a single self-contained SQLite file (an *artifact*) holding those features plus the full-text and phonetic indexes used for searching. Nothing else is installed, and the artifact is never modified after the build.

Writing a configuration is therefore an exercise in answering five questions about your data: what is one place, what identifies it, what is it called, where is it, and what else do I want to know about it.

How the Build Runs
^^^^^^^^^^^^^^^^^^

Understanding the three stages the build reports makes its error messages much easier to place:

1. **Preparing sources.** Each source file is downloaded or located on disk, extracted if it is a ZIP archive, and loaded into a table in a temporary analytical database (DuckDB). Errors here are about files and columns: a missing file, a column count that does not match, a value that will not convert to its declared type.
2. **Compiling features.** For each ``features`` block, the declared identifier, names, geometry, and data are compiled into SQL over the block's source and its joins, and run. Errors here are about your expressions: an unknown column name, an invalid join clause, an identifier that collides with another block's.
3. **Building artifact.** The projected rows are written to a temporary SQLite file, indexed, verified, compacted, and only then moved into place. A failed build leaves any previously installed artifact untouched.

Source files and staging tables are discarded afterwards. Because the sources are re-read from scratch on every build, iterating on a configuration is safe: run it again and the previous artifact is replaced atomically.

Worked Example: A Gazetteer of the Ancient World
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The rest of this section builds a working gazetteer of the ancient world from scratch, one concern at a time. Every intermediate step is a valid configuration that installs and can be queried, so you can follow along and check your results as you go.

We will use two datasets that between them exercise nearly everything a configuration can do:

- `Pleiades <https://pleiades.stoa.org/>`_, a community-built gazetteer of the ancient Mediterranean world, published as a ZIP archive of CSV exports from a relational database. It gives us places, their names in several scripts, and a controlled vocabulary of place types — spread over separate files that have to be joined back together.
- A `map of Roman provinces <https://urbesetorbis.com/>`_ at the empire's greatest extent, published as a single GeoJSON file in Web Mercator. It gives us polygons to locate the places in, in a different coordinate system from everything else.

The finished file is :download:`pleiades.yaml <../examples/pleiades.yaml>`, reproduced in full at the end of the walkthrough, so you can compare your version against it at any point. It is an example rather than a built-in gazetteer: you install it from the file, the same way you would install a configuration of your own.

.. note::

   Every step below uses ``name: pleiades``, so each build replaces the previous step's artifact — which is what you want while iterating.

Every configuration key is spelled out in these examples, including the ones that have a default, with the default noted in a comment. Real configurations usually leave those lines out; they are written here so that nothing about the file is implicit.

Step 1: Read the Data First
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Do not start with the YAML file. Start by downloading the data and looking at it, because every decision in the configuration follows from what is actually in the files.

.. code-block:: bash

   curl -O https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip
   unzip -l pleiades_gis_data.zip

The archive is about 35 MB and expands to roughly 130 MB under ``data/gis/``: seventeen CSV exports plus a README describing them. Four of those exports are relevant to us, and a fifth file comes from the second dataset:

.. list-table::
   :header-rows: 1
   :widths: 28 12 60

   * - File
     - Rows
     - What it contributes
   * - ``places.csv``
     - 42,242
     - One row per place: title, description, a representative coordinate pair, a bounding box, and the Pleiades id
   * - ``names.csv``
     - 43,708
     - One row per *name*, keyed to a place: the attested form in its original script plus up to three romanizations
   * - ``places_place_types.csv``
     - 52,511
     - Which place-type keys apply to which place — more rows than places, because a place can have several types
   * - ``place_types.csv``
     - 233
     - The place-type vocabulary: key, human-readable term, definition
   * - ``empire2.geojson``
     - 44
     - (Separate download) One MultiPolygon per Roman province

Look at the actual bytes of each file you intend to use, not just its documentation:

.. code-block:: bash

   head -2 data/gis/places.csv

.. code-block:: text

   created,description,details,provenance,title,uri,id,representative_latitude,representative_longitude,bounding_box_wkt,location_precision
   2021-11-14T03:44:08Z,"An ancient region covering a large part of southwestern Europe, ...",<p>The Barrington Atlas Directory notes: FRA</p>,Barrington Atlas: BAtlas 1 D1 Gallia,Gallia,https://pleiades.stoa.org/places/993,993,46.360953305773286,1.6706144893053327,"POLYGON ((9.6708805 31.937048, ...))",rough

Five things in those two lines already determine parts of the configuration:

- There is a **header row**, which the loader does not skip on its own (``skip_rows: 1``).
- Fields are **comma-separated** and **quoted**, and some quoted fields contain commas and even line breaks — so quoting must stay enabled (the default).
- ``id`` is a stable numeric identifier, and it is the same number that appears in the ``uri``. That is our ``identifier``.
- ``title`` is the display name, and ``representative_latitude``/``representative_longitude`` are our coordinates.
- Coordinates are plain decimal degrees, so this source's coordinate system is EPSG:4326, the same one the gazetteer stores. The provinces file will turn out not to be.

Two answers are not in this file at all: the alternate names live in ``names.csv`` and the place types in ``places_place_types.csv``. That is normal for data exported from a relational database, and joining those files back together is the bulk of the work below.

It is also worth asking what *counts* as a place here. Pleiades includes regions, rivers, roads, and ethnic groups alongside settlements, and about 7,500 of its places have no coordinates at all because they are attested in texts but have never been located. We will keep all of them: an unlocated place is still worth finding by name.

Step 2: Get One Source to Build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Resist the temptation to write the whole configuration at once. Start with a single source, an identifier, and one name, confirm that it builds, and add one thing at a time. Debugging a small configuration that just broke is far easier than debugging a large one that has never worked.

Save this as ``pleiades.yaml``:

.. code-block:: yaml

   name: pleiades
   crs: EPSG:4326 # default

   sources:
     - name: places
       url: https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip
       file: places.csv
       delimiter: ","
       quote: '"' # default
       skip_rows: 1 # header row; default is 0
       crs: EPSG:4326 # default (the gazetteer's crs)
       attributes:
         - name: "created"
           type: text
         - name: "description"
           type: text
         - name: "details"
           type: text
         - name: "provenance"
           type: text
         - name: "title"
           type: text
         - name: "uri"
           type: text
         - name: "id"
           type: integer
         - name: "representative_latitude"
           type: real
         - name: "representative_longitude"
           type: real
         - name: "bounding_box_wkt"
           type: text
         - name: "location_precision"
           type: text

   features:
     - source: places
       identifier: "id"
       names:
         - "title"

Five things about the source declaration deserve attention, because they are where first attempts usually go wrong:

- ``url`` points at the **archive**, and ``file`` names the file to take **out of** it. The archive is downloaded and unpacked automatically; you do not unpack it yourself, and you do not need to know where inside the archive the file sits. Later steps add more sources from the same archive, and it is downloaded only once per build.
- Every column of a delimited file must be declared, **in file order**, whether or not you use it. Declaring fewer columns than the file has does not drop the extras — it makes the file unparseable. ``created``, ``details``, and ``provenance`` are declared here purely to account for their position.
- Each column declares a ``type`` (``text``, ``integer``, ``real``, or ``geometry``). Choose ``text`` when unsure: an ``integer`` column that turns out to contain a non-numeric value anywhere in the file will abort the build.
- ``quote`` and ``skip_rows`` describe the *text* format of a delimited file, and only exist for such files. Both are written out here for clarity, but ``quote: '"'`` is what you get anyway.
- ``crs`` names the coordinate system this source's coordinates are in. It is spelled out here to show where it goes; since it is the same as the gazetteer's, it changes nothing. Step 8 adds a source where it does.

.. tip::

   Downloads are not kept between builds, so every step below would fetch the 35 MB archive again. Since you already have it from step 1, point the sources at your local copy while you iterate — ``path: pleiades_gis_data.zip`` instead of the ``url:`` line, resolved relative to the configuration file — and switch back to ``url`` when you are done. Everything else works identically.

Install it:

.. code-block:: bash

   python -m geoparser install pleiades.yaml

.. code-block:: text

   ─────────────────────────────────── pleiades ───────────────────────────────────

   Prepared sources                          ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:08
   Compiled features                         ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
   Built artifact                            ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01

   Summary

   Features  42,242
   Names     42,242

That is a real, queryable gazetteer:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("pleiades")
   feature = gazetteer.find("433032")

   print(feature.names)     # ['Pompeii']
   print(feature.data)      # {}
   print(feature.geometry)  # None

42,242 features and exactly one name each, which matches the row count of ``places.csv``. Getting the counts you expect at this stage is the single most useful check in the whole process: if the feature count is wrong now, the problem is in the source declaration, not in anything you add later.

Step 3: Decide What Goes into ``data``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``data`` is the feature's attribute dictionary, and you control it entirely. Each entry is written the way it would appear in a SQL ``SELECT`` list: a column name stores that column under its own name, and an optional trailing ``AS <alias>`` renames it.

.. code-block:: yaml

   features:
     - source: places
       identifier: "id"
       names:
         - "title"
       data:
         - "title"
         - "location_precision"
         - "description"
         - "uri"

.. code-block:: python

   {
     "title": "Pompeii",
     "location_precision": "precise",
     "description": "An ancient city of Campania destroyed by the volcanic eruption of Mt. Vesuvius in A.D. 79, ...",
     "uri": "https://pleiades.stoa.org/places/433032"
   }

What to include is a judgement call, guided by who reads it. Attributes exist to help a human or a resolver tell two places with the same name apart, and to point back at the source record. Type, hierarchy, and dates do that; internal revision timestamps and provenance notes generally do not, and they make the artifact bigger for nothing. ``description`` is worth its size here because Pleiades' descriptions are genuinely informative, and ``uri`` is worth including in almost any gazetteer, because it lets anyone using your data get back to the original record.

Step 4: Add Geometry
^^^^^^^^^^^^^^^^^^^^

A feature's geometry is a single value: either a geometry column of a spatial source, or an expression that constructs one. Here we build a point from the two coordinate columns:

.. code-block:: yaml

   features:
     - source: places
       identifier: "id"
       geometry: "ST_Point(representative_longitude, representative_latitude)"
       names:
         - "title"
       data:
         - "title"
         - "representative_latitude AS latitude"
         - "representative_longitude AS longitude"
         - "location_precision"
         - "description"
         - "uri"

.. warning::

   ``ST_Point`` takes **longitude first**, then latitude. Swapping them is the most common mistake in a gazetteer configuration, and it fails silently: the build succeeds, and the places end up mirrored across the globe. Check one place you know before moving on — Pompeii should be at roughly 14.49 E, 40.75 N, not 40.75 E, 14.49 N.

The build now reports the same 42,242 features, of which 34,678 have a geometry. The remaining 7,564 are the unlocated places, whose coordinate columns are empty; their geometry is simply ``NULL`` and they remain fully searchable. Storing the raw coordinates in ``data`` as well is redundant with the geometry, but convenient for anything that reads attributes rather than geometry.

.. code-block:: python

   gazetteer = Gazetteer("pleiades")
   feature = gazetteer.find("433032")

   print(feature.geometry)  # POINT (14.485429 40.74941)
   print(feature.crs)       # EPSG:4326

Step 5: Add Names from a Second File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A gazetteer is only as good as its names, and so far each place has exactly one. The real names are in ``names.csv``, one row per name, each pointing at a place through ``place_id``:

.. code-block:: text

   place_id  title      language_tag  attested_form  romanized_form_1
   433032    Pompeii    la                           Pompeii
   433032    Pompeia    grc           Πομπηία        Pompeia
   433032    Pompei     it            Pompei         Pompei
   433032    Pompei     la            Pompei         Pompei
   433032    Colonia …  la            Colonia …      Colonia …

To reach them, the feature block *joins* that file. A join is written as a raw SQL join clause, appended to the block's source; the whole joined table becomes available, and you pick what you need from it afterwards. Declare ``names`` as a second source (again with all nineteen of its columns — abbreviated here), then join it:

.. code-block:: yaml

   sources:
     - name: places
       # ... as before ...

     - name: names
       url: https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip
       file: names.csv
       delimiter: ","
       quote: '"' # default
       skip_rows: 1
       crs: EPSG:4326 # default
       attributes:
         - name: "created"
           type: text
         # ... remaining columns in file order ...
         - name: "place_id"
           type: integer
         - name: "attested_form"
           type: text
         - name: "romanized_form_1"
           type: text
         - name: "romanized_form_2"
           type: text
         - name: "romanized_form_3"
           type: text
         # ...

   features:
     - source: places
       joins:
         - "LEFT JOIN names n ON id = n.place_id"
       identifier: "id"
       geometry: "ST_Point(representative_longitude, representative_latitude)"
       names:
         - "title"
         - "n.romanized_form_1"
         - "n.romanized_form_2"
         - "n.romanized_form_3"
         - "n.attested_form"
       data:
         - "title"
         # ... as before ...

Two conventions make join clauses short. Give every joined table a **short alias** (``n`` here) and refer to its columns through it (``n.attested_form``). Columns of the block's *own* source are written **bare** (``id``, ``title``), everywhere in the block including inside the join condition — you never write a prefix for them. Use ``LEFT JOIN`` rather than ``JOIN`` unless you deliberately want to drop places that have no match: an inner join here would silently discard the 15,301 places that have no row in ``names.csv``.

The name count rises from 42,242 to 77,923, and Pompeii now carries its Latin, Greek, and Italian names:

.. code-block:: python

   print(gazetteer.find("433032").names)
   # ['Colonia Cornelia Veneria Pompeianorum', 'Pompei', 'Pompeia', 'Pompeii', 'Πομπηία']

.. warning::

   **A one-to-many join multiplies rows, and that changes what ``data`` means.** After this join, Pompeii is five rows rather than one. Names are collected across all of them, which is exactly what we want. Data values are not: each one is taken from the *first* row of the group, and among rows that a join fanned out, "first" is arbitrary. Reading ``n.language_tag`` into ``data`` would therefore store one unpredictable language per place. Use a one-to-many join to gather **names**; get **attributes** from the place's own columns or by aggregating explicitly, as in the next step.

Step 6: Clean Up the Names
^^^^^^^^^^^^^^^^^^^^^^^^^^

Names are rarely usable exactly as stored, because source data mixes names with editorial notation. A quick look through Pleiades titles shows three patterns:

.. code-block:: text

   Visurgis (river)                     qualifier in parentheses (4,295 titles)
   Sigoulones?                          uncertain identification (1,373 titles)
   Bisutun/Bagistana/Vastan?/Baptana    alternative readings, slash-separated (2,226 titles)
   [Kangavar]/Concobar                  reconstructed form in brackets (152 titles)

No text mentioning the Weser will call it "Visurgis (river)", so a feature whose only name carries a qualifier is effectively unfindable. Each ``names`` entry may be any scalar SQL expression, which is how you fix this. Build the expression up in pieces rather than all at once — strip the notation, then split what remains on the slashes, and let ``unnest`` turn the resulting list into one name per element:

.. code-block:: yaml

   names:
     - "title"
     - >-
       unnest(string_split(regexp_replace(title,
       '\s*\([^)]*\)|\?|\[|\]', '', 'g'), '/'))
     - "n.romanized_form_1"
     # ...

That single entry produces, for the four titles above, ``Visurgis``; ``Sigoulones``; ``Bisutun``, ``Bagistana``, ``Vastan``, ``Baptana``; and ``Kangavar``, ``Concobar``. The raw ``title`` is kept as a name too, so nothing is lost if the notation happens to be part of the real name. Duplicates and empty results are dropped automatically, so expressions like this are safe to be generous with.

.. tip::

   The ``>-`` is YAML's folded block scalar: it joins the following lines into one string. Long expressions become far easier to read that way, and — unlike a quoted string — backslashes need no doubling, so regular expressions can be written exactly as SQL sees them.

The name count rises to 79,578. Whether an expression like this is worth writing depends on your data; the way to find out is to sort your name column and read a few hundred values, which takes ten minutes and tells you more than any amount of guessing.

Step 7: Aggregate a Many-to-Many Relation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Place types are the single most useful attribute for telling same-named places apart, and in Pleiades they sit behind two more files: ``places_place_types.csv`` maps places onto type keys, and ``place_types.csv`` translates those keys into readable terms. A place may have several types.

The obvious approach is to join both files and read the term:

.. code-block:: yaml

   # Don't do this
   joins:
     - "LEFT JOIN names n ON id = n.place_id"
     - "LEFT JOIN places_place_types x ON id = x.place_id"
     - "LEFT JOIN place_types t ON x.place_type = t.key"
   data:
     - "t.term AS place_type"

This builds, and it is wrong in the way the previous step warned about. Pompeii is both a ``settlement`` and an ``urban area``; the join fans it out and ``data`` keeps one of the two, unpredictably. It also demonstrates a **chained join** — the second clause joins to a table the first one brought in — which is the right pattern when the relation is many-to-*one* (a code and its label), just not here.

What we want is all of a place's types in one value. Because ``data`` entries are arbitrary scalar expressions, a subquery can aggregate the relation without fanning out any rows:

.. code-block:: yaml

   data:
     - "title"
     - >-
       (SELECT string_agg(DISTINCT coalesce(t.term, x.place_type), ', '
       ORDER BY coalesce(t.term, x.place_type))
       FROM places_place_types x
       LEFT JOIN place_types t ON x.place_type = t.key
       WHERE x.place_id = id)
       AS place_types
     # ... as before ...

The subquery reads the bridge table for one place (``WHERE x.place_id = id``, where ``id`` is the current place's own column), looks each key up in the vocabulary, and joins the results into a single string. It is an ordinary SQL query with its own ``FROM`` and its own join, and the only thing tying it to the feature being built is that one reference to ``id``.

The ``coalesce`` is there because 1,904 rows of the bridge table reference keys that are missing from the vocabulary file entirely; without it, those places would silently lose a type. The ``ORDER BY`` is not cosmetic either: without it the aggregation order is unspecified, and rebuilding the same configuration would produce different strings for multi-type places. Pompeii now gets ``"settlement, urban area"``, stably.

The two new sources are declared like any other, and note that neither is named in any ``features`` block. A source that only supports a join or an expression still has to be declared, and simply never backs features of its own:

.. code-block:: yaml

     - name: places_place_types
       url: https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip
       file: places_place_types.csv
       delimiter: ","
       quote: '"' # default
       skip_rows: 1
       crs: EPSG:4326 # default
       attributes:
         - name: "place_id"
           type: integer
         - name: "place_type"
           type: text

     - name: place_types
       url: https://atlantides.org/downloads/pleiades/gis/pleiades_gis_data.zip
       file: place_types.csv
       delimiter: ","
       quote: '"' # default
       skip_rows: 1
       crs: EPSG:4326 # default
       attributes:
         - name: "key"
           type: text
         - name: "term"
           type: text
         - name: "definition"
           type: text
         - name: "same_as"
           type: text
         - name: "uri"
           type: text

Step 8: Join a Spatial Source
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pleiades has no administrative hierarchy — no "in Italy, in Campania" to disambiguate with. We can compute one instead: given polygons of the Roman provinces, a place's province is whichever polygon contains its point. This is a **spatial join**, and it is the main reason to bring a second dataset in.

A **spatial source** is any file the build can read geometry from — Shapefile, GeoPackage, GeoJSON, and other GDAL-supported formats. It is distinguished from a tabular source by having no ``delimiter``, and it declares exactly one attribute of type ``geometry``, always named ``geometry``:

.. code-block:: yaml

     - name: provinces
       url: https://urbesetorbis.com/downloads/empire2.geojson
       file: empire2.geojson
       crs: EPSG:3857 # Web Mercator, unlike the rest
       attributes:
         - name: "fid"
           type: integer
         - name: "Title"
           type: text
         - name: "Government"
           type: text
         - name: "StartYear"
           type: integer
         - name: "geometry"
           type: geometry

Three differences from a tabular source matter. The two text-format keys are gone: a spatial format carries its own field names, so there is no header row to skip and nothing to unquote, and declaring ``skip_rows`` or ``quote`` on such a source is an error rather than a no-op. Unlike a delimited file, a spatial source also selects its fields **by name**, so it may declare a subset of them, in any order: this file additionally carries a ``color`` field, which is simply left out. And ``crs`` finally does something, because this file is in Web Mercator rather than the degrees the gazetteer stores.

That last point is worth dwelling on, because in most geospatial tooling it is where the work starts. Here it is where it ends: declaring ``crs: EPSG:3857`` is the whole of it. Geometries are re-projected into the gazetteer's coordinate system as the source is read, before any of your expressions see them, so from the configuration's point of view every geometry in every source is already in the same system. Now the join:

.. code-block:: yaml

   joins:
     - "LEFT JOIN names n ON id = n.place_id"
     - >-
       LEFT JOIN provinces p
       ON ST_Within(ST_Point(representative_longitude, representative_latitude),
       p.geometry)
   data:
     # ...
     - "p.Title AS province"
     - "p.Government AS province_government"

A spatial join reads exactly like an attribute join, except that the condition is a spatial predicate — ``ST_Within``, ``ST_Intersects``, ``ST_Contains``, and so on — instead of an equality. Here it asks which province polygon contains the place's point, with no coordinate handling of any kind: degrees on the left, degrees on the right, because the polygons were converted on the way in. For lines and polygons, reduce one side to a representative point with ``ST_Centroid`` if the predicate needs it.

.. note::

   The one geometry that is *not* converted for you is one you build yourself out of plain number columns, such as ``ST_Point(lon, lat)`` on a source whose ``crs`` is not the gazetteer's. Those columns are numbers like any other, and the build has no way to know which of them are coordinates. It is handled where it matters — a feature's own ``geometry`` is transformed from its source's ``crs`` — but inside a join condition you would have to write ``ST_Transform`` yourself. It does not come up here, since Pleiades' coordinates are already in degrees.

26,887 of the 34,678 located places fall inside a province; the rest are outside the empire, or in it at a different date. Because ``provinces`` is a many-to-one relation, reading two of its columns into ``data`` is safe here.

Step 9: Consider a Second Kind of Place
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

So far every feature comes from one file. A configuration may instead have as many ``features`` blocks as it has sources, each projecting a different file, with its own identifier scheme, geometry, names, and attributes. This is how a gazetteer holds genuinely different kinds of place — settlements from one dataset, administrative areas from another — in one artifact.

The provinces would be the obvious candidate here, since ancient texts name them constantly. A block over that source would look like this:

.. code-block:: yaml

   features:
     - source: places
       # ... the block from step 8 ...

     - source: provinces
       identifier: "'province:' || fid"
       geometry: "geometry"
       names:
         - "Title"
         - "unnest(string_split(Title, ' et '))"
       data:
         - "Title AS title"
         - "'Roman province' AS place_types"
         - "Government AS government"
         - "StartYear AS start_year"

Four things are worth pointing out in those ten lines, because they are what a second block always has to get right:

- **Identifiers must be unique across the whole gazetteer, not just within a block.** The provinces' own ``fid`` values are 1 to 44, which would collide with Pleiades place ids; the expression prefixes them, giving ``province:1`` and so on. If two blocks ever do produce the same identifier, the build fails and names the collision rather than silently merging two places.
- ``geometry: "geometry"`` takes the polygon straight from the spatial source, in place of a point built from coordinates. Nothing else about the block changes because its geometry happens to be a MultiPolygon.
- Several provinces are administrative pairings, so ``unnest(string_split(Title, ' et '))`` makes ``Creta`` and ``Cyrenaica`` findable alongside ``Creta et Cyrenaica``.
- ``'Roman province' AS place_types`` stores a constant. Blocks are free to store completely different attributes, and usually do — but it is worth agreeing on a few keys, here ``title`` and ``place_types``, so that anything reading the gazetteer finds them on every feature whatever it came from.

We will leave it out all the same, and the reason is a good illustration of what to think about before adding a block. Pleiades already contains the provinces: ``Sicilia (Roman province)``, ``Dacia (province)`` and the rest are places in ``places.csv``, with descriptions, alternative names, and Pleiades ids. Adding the polygons as features would duplicate every one of them under a second identifier, so a text mentioning Sicilia would produce two candidates that are the same province, differing only in whether it is drawn as a point or an area. The provinces dataset earns its place in this gazetteer as the *boundaries* that locate places, which is what step 8 uses it for, and not as a second set of places.

A second block is worth adding when the source contributes places the first one does not have. If your boundaries came from a dataset with no counterpart in your main file, everything above is exactly what you would write.

Step 10: Use the Finished Gazetteer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The configuration is now complete; it is reproduced in full at the end of this walkthrough. Installed, it takes well under a minute and 0.6 GB of working disk space, and produces an artifact of about 23 MB with 42,242 features and 79,578 names. That measured figure is what the file's ``disk`` key declares, so that a build with too little room to finish says so before it starts rather than halfway through:

.. code-block:: bash

   python -m geoparser install pleiades.yaml
   python -m geoparser list

Check it from the outside before trusting it. Look up places you know and confirm the names, attributes, and coordinates are what you expect:

.. code-block:: python

   from geoparser import Gazetteer

   gazetteer = Gazetteer("pleiades")

   for feature in gazetteer.search("Sicilia", method="exact"):
       print(feature.identifier, feature.data["title"],
             "|", feature.data["place_types"], "|", feature.geometry.geom_type)

.. code-block:: text

   462492  Sicilia (island)          | island   | Point
   981549  Sicilia (Roman province)  | province | Point

Then point a resolver at it. A resolver describes each candidate place in words before comparing it against the text, so it needs to know which of *your* attribute keys carry the name, the type, and the enclosing places. That mapping is the ``attribute_map``:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   resolver = SentenceTransformerResolver(
       gazetteer_name="pleiades",
       attribute_map={
           "name": "title",
           "type": "place_types",
           "level1": "province",
       },
   )
   geoparser = Geoparser(recognizer=SpacyRecognizer(), resolver=resolver)

``name`` and ``type`` must both be present; add as many of ``level1`` to ``level3`` as your data supports, where ``level1`` is the outermost enclosing place and ``level3`` the innermost. Pleiades has only one such level, the province we computed in step 8. With the map above, a candidate is described as ``Pompeii (settlement, urban area) in Italia``, which is what gets compared against the surrounding text. The built-in gazetteers carry this mapping already; a gazetteer of your own always needs it passed in.

Step 11: Expect to Retune the Modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A finished gazetteer is not the end of the work, because the default recognizer and resolver were not chosen with your data in mind. Two mismatches show up immediately with a gazetteer as far from the defaults as this one:

- **The recognizer may not find your placenames.** The default spaCy model was trained on contemporary news text, and in *"Pliny describes the eruption that buried Pompeii and Herculaneum in Campania"* it labels ``Campania`` as a place but misses ``Pompeii`` and ``Herculaneum`` entirely. What the gazetteer contains is irrelevant if nothing is recognized to look up. Try a larger spaCy model, a model trained on your domain, or supply the spans yourself with a manual recognizer.
- **The resolver's threshold may be tuned for other data.** The default embedding model is fine-tuned on GeoNames-style descriptions, so descriptions like ``Campania (region) in Italia`` sit lower on its similarity scale than the default ``min_similarity`` of 0.6 expects: the correct candidate scores 0.55 and is rejected, after which the resolver widens its search and settles on a worse one. Lowering the threshold to 0.45 resolves ``Campania`` correctly.

Neither is a fault in the configuration, and neither is visible from the build output — which is why it is worth resolving a handful of names you know the answer to, and inspecting the candidates and their scores when one comes out wrong. :doc:`modules` covers the parameters, and :doc:`training` covers fine-tuning a resolver against your own gazetteer, which is the real fix: the default models are optimized for GeoNames, and training on data annotated with your gazetteer's features is the recommended way to close the gap.

The Complete Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is everything the walkthrough built, in one file — :download:`pleiades.yaml <../examples/pleiades.yaml>`:

.. literalinclude:: ../examples/pleiades.yaml
   :language: yaml

At this point you have used every mechanism the configuration format offers: tabular and spatial sources, archives and plain files, attribute joins, chained joins, one-to-many joins, spatial joins across coordinate systems, derived names, aggregated attributes, and multiple feature blocks. The reference below fills in the details.

Configuration Reference
~~~~~~~~~~~~~~~~~~~~~~~

A configuration has two top-level lists. ``sources`` declares the files to read and what is in them. ``features`` declares how the rows of a source become places. Sources are transient — they are staged for the build and discarded — so the ``features`` blocks are what actually shapes the gazetteer.

Top-Level Keys
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - Key
     - Meaning
   * - ``name``
     - The gazetteer's name, used to install, query, and uninstall it. Letters, digits, underscores, and hyphens. Installing a configuration replaces any artifact of the same name.
   * - ``crs``
     - Coordinate reference system all geometries are stored in. Defaults to ``EPSG:4326``. Sources in other systems are reprojected into it at build time.
   * - ``disk``
     - Optional. Free bytes required on the gazetteers volume, checked before the build starts. Leave it out until you have measured what a build actually costs; a guessed value either blocks builds that would have worked or fails to catch the ones that will not.
   * - ``sources``
     - List of source declarations. At least one.
   * - ``features``
     - List of feature blocks. At least one.

Sources
^^^^^^^

A source is one file to read. It is **tabular** if it declares a ``delimiter``, and **spatial** otherwise.

.. list-table::
   :header-rows: 1
   :widths: 14 86

   * - Key
     - Meaning
   * - ``name``
     - Identifies the source within the configuration, and is the name used to join it. Must be a valid SQL identifier: letters, digits, and underscores, not starting with a digit.
   * - ``url``
     - Where to download the file from. Exactly one of ``url`` or ``path`` is required. Several sources may name the same URL, in which case it is downloaded once per build; the downloads are discarded when the build finishes.
   * - ``path``
     - A local file or directory instead of a download. Relative paths resolve against the configuration file's own directory, so a configuration and its data can be moved together.
   * - ``file``
     - The file to actually read. When ``url`` or ``path`` points at a ZIP archive or a directory, it is searched recursively for a file of this name; otherwise it must match the file's own name.
   * - ``delimiter``
     - Field separator of a delimited text file (``","``, ``"\t"``, ``"|"``). Its presence is what makes a source tabular.
   * - ``quote``
     - Quote character for tabular sources, ``"`` by default. Set it to ``""`` to disable quote handling entirely, which is what raw tab-separated exports need — GeoNames files contain unbalanced quote characters inside ordinary values.
   * - ``skip_rows``
     - Leading lines of a tabular file to discard: ``1`` for a header row, more for licence preambles. Nothing is skipped by default, and a header row that is not skipped becomes a feature.
   * - ``crs``
     - Coordinate reference system this source's geometry and coordinates are in. Defaults to the gazetteer's ``crs``. Geometry is converted as the source is read, so the rest of the configuration works in one system.
   * - ``attributes``
     - The source's columns, each with a ``name`` and a ``type``.

``delimiter``, ``quote`` and ``skip_rows`` describe a delimited text file and are rejected on a spatial source. Attribute types are ``text``, ``integer``, ``real``, and ``geometry``, and two rules differ between the two kinds of source:

- A **tabular** source must declare **every** column, in file order, and may not declare a ``geometry`` attribute. The declaration is the file's schema, so a mismatch in count makes the file unparseable rather than dropping columns.
- A **spatial** source may declare any **subset** of the file's fields, in any order, and must declare exactly **one** attribute of type ``geometry``, named ``geometry``.

Several sources may point at the same ``url`` with different ``file`` values, which is how a multi-file archive is used; it is downloaded once.

Feature Blocks
^^^^^^^^^^^^^^

Each block turns the rows of one source into features. A source backs at most one block, and the block's ``source`` name is what appears as ``feature.source`` in the artifact.

.. list-table::
   :header-rows: 1
   :widths: 14 86

   * - Key
     - Meaning
   * - ``source``
     - The source whose rows this block projects.
   * - ``joins``
     - Optional list of raw SQL join clauses that widen those rows with columns from other sources.
   * - ``identifier``
     - The feature's stable identifier. Must read only the block's own source. Rows where it evaluates to ``NULL`` are skipped.
   * - ``geometry``
     - Optional. The feature's geometry, as a geometry column or an expression building one. Must read only the block's own source.
   * - ``names``
     - One or more names, each a column or expression. At least one is required.
   * - ``data``
     - Optional attributes, each written as it would appear in a SQL ``SELECT`` list.

Blocks are written in reading order — source, joins, then everything derived from them.

Values and Expressions
^^^^^^^^^^^^^^^^^^^^^^

``identifier``, ``geometry``, every ``names`` entry, and every ``data`` entry is either a column reference or a scalar SQL expression, and one rule covers all of them: **a bare name is a column of the block's own source; a column of a joined source is written ``<alias>.<column>``.** The same rule applies inside join conditions, so nothing in a block ever needs a prefix for its own columns.

Expressions are evaluated by DuckDB, so its `scalar function library <https://duckdb.org/docs/stable/sql/functions/overview>`_ is available: string manipulation, ``CASE``, arithmetic, regular expressions, ``ST_`` spatial constructors, and subqueries over any declared source. Some patterns that come up repeatedly:

.. code-block:: yaml

   # Names
   - "name"                                              # a column
   - "unnest(string_split(alternatenames, ','))"         # one name per value of a multi-value column
   - "regexp_replace(name, '\\s*\\(.*\\)', '')"          # strip a parenthesised qualifier
   - "n.attested_form"                                   # a column of a joined source

   # Geometry
   - "geometry"                                          # a spatial source's geometry column
   - "ST_Point(longitude, latitude)"                     # built from coordinate columns (longitude first)
   - "ST_GeomFromText(geometry_wkt)"                     # parsed from a WKT text column

   # Data
   - "population"                                        # stored under its own name
   - "c.Country AS country_name"                         # a joined column, renamed
   - "upper(name) AS name_upper"                         # an expression (alias required)
   - "'Roman province' AS place_types"                   # a constant

A ``data`` entry that is a plain column reference may omit the alias, in which case the column's own name is the key; anything else has no name of its own and must be given one. Two entries may not store the same key.

A name expression may return a list, in which case each element becomes its own name — that is what ``unnest`` is for. Names that come out ``NULL``, empty, or whitespace are dropped, and duplicates are collapsed, so name expressions can be written generously.

Joins
^^^^^

A join is a raw SQL join clause appended to the block's source. The whole joined table becomes available; there is no separate list of columns to import, you simply reference what you need in ``data``.

.. code-block:: yaml

   joins:
     # Attribute join: match on equal values
     - "LEFT JOIN countryInfo c ON country_code = c.ISO"
     # Match on an expression
     - "LEFT JOIN admin1CodesASCII a1 ON country_code || '.' || admin1_code = a1.code"
     # Chained join: reference a table joined earlier
     - "LEFT JOIN admin2Codes a2 ON a1.code || '.' || admin2_code = a2.code"
     # Spatial join
     - "LEFT JOIN municipalities g ON ST_Within(ST_Centroid(geometry), g.geometry)"

Joins are applied in order, so a later clause may reference any table an earlier one brought in; that is how multi-level hierarchies (place → municipality → district → canton) are expressed. Prefer ``LEFT JOIN``: an inner join drops the rows that have no match, which quietly removes places from your gazetteer.

The property of joins that causes most of the surprises is cardinality, because it changes what ``data`` means. A many-to-one join is safe. A one-to-many join multiplies the rows of a place, and while ``names`` are collected across all of them, each ``data`` value is taken from the first row of the group — arbitrary among rows produced by a fan-out. Gather names with a one-to-many join; aggregate attributes with a subquery instead.

Coordinate systems, on the other hand, take care of themselves. Every source's geometry is converted to the gazetteer's ``crs`` as it is read, so a spatial join between sources published in different systems needs nothing written for it. The exception is a geometry you construct from plain number columns, such as ``ST_Point(lon, lat)`` over a source whose ``crs`` is not the gazetteer's: the build cannot tell which columns hold coordinates, so it transforms such an expression only where it is used as a feature's ``geometry``. Inside a join condition, wrap it in ``ST_Transform`` yourself.

Duplicate Identifiers
^^^^^^^^^^^^^^^^^^^^^

Within one block, rows that share an identifier are **merged into a single feature**: all their names are collected, their geometries are unioned into one possibly multi-part geometry, and each data value is taken from the first row. This is automatic, and it is how datasets that spread a place over several records — multi-part geometries, one row per name — end up as one place.

.. code-block:: text

   p1  North Summit  800     →  one feature "p1", names {North Summit, South Summit},
   p1  South Summit  1200       height 800, geometry MultiPoint of both rows
   p2  Lone Hill     300      →  one feature "p2"

Across blocks it is an error instead: identifiers must be unique in the whole gazetteer, and a collision fails the build with the offending identifier and the blocks it came from. Namespace them with an expression (``"'province:' || fid"``) or merge the blocks.

What the Format Does Not Do
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Knowing the limits saves time looking for keys that do not exist:

- **There is no row filter.** A block has no ``where``. To exclude rows, make the ``identifier`` evaluate to ``NULL`` for them, since rows without an identifier are skipped: ``identifier: "CASE WHEN feature_class <> 'X' THEN id END"``. To filter *joined* rows, add the condition to the join instead: ``"LEFT JOIN names n ON id = n.place_id AND n.association_certainty = 'certain'"``.
- **``identifier`` and ``geometry`` must come from the block's own source.** Only ``names`` and ``data`` can read joined columns. A qualified reference in either is rejected at the start of the build with an explicit message.
- **One block per source.** To project one file into two kinds of feature, declare it twice under different source names.
- **No user code.** Transformations are limited to SQL expressions evaluated during the build. Anything that needs real preprocessing has to happen before the build, on a file you then reference with ``path``.
- **Names are unordered and unlabelled.** There is no notion of a preferred name or a name's language in the search index. Store that in ``data`` if you need it.

Installing and Iterating
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python -m geoparser install path/to/my_gazetteer.yaml
   python -m geoparser list
   python -m geoparser uninstall my_gazetteer

The build validates the configuration, acquires the files, runs the projections, and writes the artifact. If anything is wrong, it stops with a message and nothing is installed; a successful build atomically replaces any previous artifact of the same name, so iterating on a configuration is safe.

Downloaded files are discarded once the build finishes, which means every rebuild fetches them again. While you are still changing a configuration, download the files once by hand and point the sources at them with ``path`` instead of ``url``; each iteration then costs only the processing time.

.. note::

   Building a gazetteer with geometries needs DuckDB's spatial extension, which is fetched automatically the first time. To build offline, run one spatial build while connected first so the extension is cached.

Further Examples
^^^^^^^^^^^^^^^^

The built-in gazetteers are configured exactly the same way, and their files are worth reading once you have your own working: `geonames.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames.yaml>`_ (a large tabular dataset with four lookup joins), `geonames-cities.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/geonames-cities.yaml>`_ (four feature blocks over overlapping sources), and `swissnames3d.yaml <https://github.com/dguzh/geoparser/blob/main/geoparser/gazetteer/configs/swissnames3d.yaml>`_ (six spatial sources, chained spatial joins, and multi-part geometry merging).

Next Steps
----------

Now that you understand gazetteers, you can explore:

- :doc:`modules` - Learn how resolvers use gazetteers for disambiguation
- :doc:`training` - Train resolvers on specific gazetteers for better performance
- :doc:`projects` - Use projects to organize work with different gazetteers

For complete API documentation of gazetteer classes, see the :doc:`../api/gazetteer` reference.
