.. _results:

Working with Results
====================

This guide describes what a pipeline gives you back and how to read it: the three kinds of object a parse produces, the attributes each one carries, and the two cases — an unresolved name and a missing attribute — that any code reading results has to allow for.

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

.. code-block:: text

   Zurich 27 33 Feature(geonames:2657896)
   Geneva 60 66 Feature(geonames:2660646)
   Basel 71 76 Feature(geonames:2661604)

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

Full signatures for all three are in the :doc:`../api/models` reference.

Toponyms
--------

A toponym is a place name as it was found in the text. ``text`` is the name as written, which need not be the gazetteer's name for the place: the toponym above reads ``Zurich``, while GeoNames names that city ``Zürich``.

``start`` and ``end`` are character offsets into ``document.text``, with ``end`` exclusive, so ``document.text[toponym.start:toponym.end]`` gives the toponym back and a wider slice gives the text around it.

Locations
---------

A location is a ``Feature``: one entry in the gazetteer the resolver was using.

``data`` holds that gazetteer's attributes for the place, as a dictionary. Which keys exist depends on the gazetteer, and can differ between sources within one gazetteer, so read them with ``.get()``:

.. code-block:: python

   data = toponym.location.data
   print(data.get("name"), data.get("country_name"), data.get("feature_name"))

``identifier`` is the gazetteer's stable id for the place. It is what to store when you need a reference that survives — in annotations, in exported data, in anything you come back to — and what to group or count by. Names are not unique: GeoNames has 122 places called Paris, so counting by ``data["name"]`` silently merges places that happen to share a name, while counting by ``identifier`` does not.

``geometry`` is a Shapely object — usually a point, but lines, polygons, and multi-part geometries occur — expressed in the coordinate reference system named by ``crs``, which is ``EPSG:4326`` for both pre-configured gazetteers. Because it is a Shapely object, it can be measured, transformed, or handed to any library that reads Shapely geometries.

``names`` lists every string the place is searchable by, and ``source`` names the gazetteer source the feature came from, which is how features of different kinds within one gazetteer can be told apart.

What May Be Missing
-------------------

Two things are absent often enough that reading results means allowing for them.

**A toponym may have no location.** ``toponym.location`` is ``None`` when a name was recognized but not resolved, either because the place is not in the gazetteer or because no candidate passed the resolver's similarity threshold.

.. code-block:: python

   for toponym in document.toponyms:
       if toponym.location is None:
           print(f"{toponym.text}: unresolved")
           continue
       print(f"{toponym.text}: {toponym.location.data.get('name')}")

**A location may lack an attribute or a geometry.** Attributes are absent wherever the gazetteer has nothing to record: the Pacific Ocean, for instance, has no ``country_name``. ``geometry`` can likewise be ``None`` — every GeoNames entry has coordinates, but a gazetteer you build yourself need not give all of its places a geometry.

.. code-block:: python

   geometry = toponym.location.geometry
   if geometry is not None:
       print(geometry.x, geometry.y)

Which of these you see says something about your setup rather than about the library. A name that recurs in your corpus and never resolves usually means the gazetteer does not cover that kind of place, or that the resolver's threshold is too high for your material — see :doc:`modules`. It is also worth parsing whole paragraphs rather than isolated sentences, since the resolver uses the words around a name to choose between places that share it — see :ref:`quickstart-context`.

Taking Results Elsewhere
------------------------

Everything above is ordinary Python data — strings, numbers, dictionaries, and Shapely geometries — so results go into whatever you already use by walking the structure once and keeping the fields you need:

.. code-block:: python

   documents = geoparser.parse(texts)

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
                   "gazetteer_id": location.identifier if location else None,
                   "name": data.get("name"),
                   "latitude": data.get("latitude"),
                   "longitude": data.get("longitude"),
               }
           )

One row per toponym, as above, is the shape most tabular and spatial tools expect. Note that ``parse()`` mirrors its input, so a single string gives you one document rather than a list; wrap it before iterating, or pass a list in the first place.

Relating Results to Your Own Records
------------------------------------

Parsed documents are usually a means to an end: you had records — articles, interviews, files — and you want the geography attached to those.

With ``Geoparser.parse()``, order is the link. A list of texts returns a list of documents in the same order:

.. code-block:: python

   documents = geoparser.parse([article["body"] for article in articles])

   for article, document in zip(articles, documents):
       article["places"] = [
           t.location.identifier for t in document.toponyms if t.location
       ]

For anything larger, or anything you may want to revisit, use a :doc:`project <projects>` and keep the document identifiers it gives you. Those survive between sessions, where positional order does not.

Keeping Results
---------------

``Geoparser.parse()`` discards its work once it returns. To keep it, pass ``save=True``:

.. code-block:: python

   document = geoparser.parse("Berlin is the capital of Germany.", save=True)

.. code-block:: text

   Results saved under project name: a1b2c3d4

The printed name is how you get back to those results, via ``Project("a1b2c3d4")``. Since a randomly generated name is awkward to remember, prefer creating a project with a name you chose whenever you know in advance that you want to keep the output. See :doc:`projects`.
