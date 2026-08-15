.. _results:

Working with Results
====================

Parsing text is rarely the last step. This guide covers what comes out of a pipeline, how to get at it, and how to turn it into the formats you will actually analyse in — tables, spreadsheets, and spatial files.

The Shape of the Output
-----------------------

Whatever you parse, you get **documents**. Each document holds the **toponyms** found in it, and each toponym may hold the **location** it resolved to.

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )

   document = geoparser.parse(
       "The conference was held in Zurich, with satellite events in Geneva and Basel."
   )

   for toponym in document.toponyms:
       print(toponym.text, toponym.start, toponym.end, toponym.location)

Three levels, each answering a different question:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Object
     - What you get from it
   * - ``Document``
     - ``text``, ``id``, and ``toponyms``
   * - ``Reference`` (a toponym)
     - ``text`` as written, ``start`` and ``end`` character offsets, and ``location``
   * - ``Feature`` (a location)
     - ``identifier``, ``data`` attributes, ``geometry``, ``crs``, ``names``, ``source``

The offsets are the useful part people overlook: they let you go back to the text. ``document.text[toponym.start:toponym.end]`` is the toponym, and widening the slice gives you the sentence it sat in — which is what you want for keyword-in-context tables or for checking a suspicious result by eye.

Always Check for ``None``
-------------------------

``toponym.location`` is ``None`` when the name was recognized but not resolved. This is normal and expected: the place may be absent from the gazetteer, or no candidate may have been convincing enough. The resolver prefers admitting uncertainty to guessing.

.. code-block:: python

   for toponym in document.toponyms:
       if toponym.location is None:
           print(f"{toponym.text}: unresolved")
           continue
       data = toponym.location.data
       print(f"{toponym.text}: {data.get('name')}, {data.get('country_name')}")

Read attributes with ``.get()`` rather than ``data["name"]``. Which keys exist depends on the gazetteer, and even on the source within one gazetteer, so subscripting works until it suddenly does not. Geometry needs the same care — a place known by name but never located has none:

.. code-block:: python

   geometry = toponym.location.geometry
   if geometry is not None:
       print(geometry.x, geometry.y)

Flattening to Rows
------------------

Almost every downstream use starts by turning the nested structure into one row per toponym. This is the single most useful piece of code to have on hand:

.. code-block:: python

   def to_rows(documents):
       """Flatten parsed documents into one dictionary per toponym."""
       rows = []
       for document in documents:
           for toponym in document.toponyms:
               location = toponym.location
               data = location.data if location else {}
               rows.append(
                   {
                       "document_id": str(document.id),
                       "toponym": toponym.text,
                       "start": toponym.start,
                       "end": toponym.end,
                       "resolved": location is not None,
                       "gazetteer_id": location.identifier if location else None,
                       "name": data.get("name"),
                       "country": data.get("country_name"),
                       "feature_type": data.get("feature_name"),
                       "latitude": data.get("latitude"),
                       "longitude": data.get("longitude"),
                   }
               )
       return rows

Note that ``parse()`` mirrors its input: a single string gives you one document, a list gives you a list. Wrap a single document in a list before flattening, or pass a list in the first place.

.. code-block:: python

   documents = geoparser.parse([
       "The conference was held in Zurich, with satellite events in Geneva and Basel.",
       "Researchers in Nairobi and Mombasa collected samples along the Kenyan coast.",
   ])

   rows = to_rows(documents)

Pass whole paragraphs or documents rather than isolated sentences. The resolver uses the words around a name to choose between places that share it, so short decontextualized snippets resolve markedly worse — see :ref:`quickstart-context`.

Writing a CSV
-------------

With rows in hand, the standard library is enough — no extra dependency:

.. code-block:: python

   import csv

   rows = to_rows(documents)

   with open("toponyms.csv", "w", newline="", encoding="utf-8") as handle:
       writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
       writer.writeheader()
       writer.writerows(rows)

Write ``encoding="utf-8"`` explicitly. Place names carry diacritics and non-Latin scripts, and on Windows the default encoding will mangle them.

Using pandas
------------

If you have pandas installed, the same rows become a dataframe directly, and the usual summarizing follows:

.. code-block:: python

   import pandas as pd

   frame = pd.DataFrame(to_rows(documents))

   # How much resolved?
   print(frame["resolved"].mean())

   # Most frequently mentioned places
   print(frame[frame["resolved"]].groupby("name").size().sort_values(ascending=False).head(10))

   # Which names failed to resolve, and how often
   print(frame[~frame["resolved"]]["toponym"].value_counts())

That last query is worth running every time. A recurring unresolved name usually means something systematic — a gazetteer that does not cover the place type you care about, a threshold set too high, or a spelling convention in your corpus — and it is much easier to see in aggregate than one document at a time.

Counting Mentions per Place
---------------------------

Frequency by place is the most common summary, and it has one trap: group by the gazetteer **identifier**, not by the name. Two different places genuinely share a name, and collapsing them silently merges them.

.. code-block:: python

   from collections import Counter

   counts = Counter(
       toponym.location.identifier
       for document in documents
       for toponym in document.toponyms
       if toponym.location is not None
   )

   for identifier, count in counts.most_common(10):
       feature = next(
           t.location
           for d in documents
           for t in d.toponyms
           if t.location and t.location.identifier == identifier
       )
       print(f"{feature.data.get('name')}: {count}")

Keeping Context
---------------

To inspect results, or to build a concordance, slice the document text around each toponym:

.. code-block:: python

   WINDOW = 60

   for document in documents:
       for toponym in document.toponyms:
           left = max(0, toponym.start - WINDOW)
           right = min(len(document.text), toponym.end + WINDOW)
           snippet = document.text[left:right].replace("\n", " ")
           resolved = toponym.location.data.get("name") if toponym.location else "—"
           print(f"{toponym.text} → {resolved}\n    …{snippet}…")

Reading twenty of these is the fastest way to judge whether a pipeline is working on your material. Aggregate numbers tell you how much resolved; only the snippets tell you whether it resolved *correctly*.

Exporting Spatial Data
----------------------

Every located feature has a Shapely ``geometry`` in the gazetteer's coordinate reference system, which you can read from ``feature.crs`` — ``EPSG:4326`` (longitude/latitude in degrees) for both pre-configured gazetteers.

For GeoJSON, the standard library suffices. GeoJSON requires ``EPSG:4326``, which is what you already have:

.. code-block:: python

   import json
   from shapely.geometry import mapping

   features = []
   for document in documents:
       for toponym in document.toponyms:
           location = toponym.location
           if location is None or location.geometry is None:
               continue
           features.append(
               {
                   "type": "Feature",
                   "geometry": mapping(location.geometry),
                   "properties": {
                       "toponym": toponym.text,
                       "name": location.data.get("name"),
                       "country": location.data.get("country_name"),
                       "document_id": str(document.id),
                   },
               }
           )

   with open("toponyms.geojson", "w", encoding="utf-8") as handle:
       json.dump({"type": "FeatureCollection", "features": features}, handle)

The result opens directly in QGIS, ArcGIS, or any web mapping library.

If you work with GeoPandas, you get Shapefile, GeoPackage, and reprojection for free:

.. code-block:: python

   import geopandas as gpd

   records = []
   for document in documents:
       for toponym in document.toponyms:
           location = toponym.location
           if location is None or location.geometry is None:
               continue
           records.append(
               {
                   "geometry": location.geometry,
                   "toponym": toponym.text,
                   "name": location.data.get("name"),
                   "country": location.data.get("country_name"),
               }
           )

   frame = gpd.GeoDataFrame(records, crs="EPSG:4326")
   frame.to_file("toponyms.gpkg", driver="GPKG")

Set ``crs`` from ``feature.crs`` rather than hard-coding it if you use a custom gazetteer, since a gazetteer chooses its own coordinate system at build time. GeoPandas is not a dependency of this library; install it separately if you want it.

Relating Results Back to Your Own Records
-----------------------------------------

Parsed documents are usually a means to an end: you had records — articles, interviews, files — and you want the geography attached to *them*, not to an anonymous list.

With ``Geoparser.parse()``, order is the link. A list of texts returns a list of documents in the same order, so zipping is safe:

.. code-block:: python

   articles = load_articles()   # your own records, whatever shape they have

   documents = geoparser.parse([article["body"] for article in articles])

   for article, document in zip(articles, documents):
       article["places"] = [
           t.location.data.get("name")
           for t in document.toponyms
           if t.location is not None
       ]

For anything larger, or anything you might want to revisit, use a :doc:`project <projects>` instead and keep the document identifiers it gives you. Those survive between sessions, where positional order does not.

Saving Results for Later
------------------------

``Geoparser.parse()`` discards its work once it returns. To keep it, pass ``save=True``:

.. code-block:: python

   document = geoparser.parse("Berlin is the capital of Germany.", save=True)

.. code-block:: text

   Results saved under project name: a1b2c3d4

The printed name is how you get back to those results, via ``Project("a1b2c3d4")``. Since a randomly generated name is awkward to remember, prefer creating a project with a name you chose whenever you know in advance that you want to keep the output. See :doc:`projects`.

Next Steps
----------

If your results look thin — few toponyms found, or many unresolved — the fix is usually in the modules rather than in this code. Continue to :doc:`modules`.
