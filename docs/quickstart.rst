.. _quickstart:

Quickstart
==========

This is a single worked example, built up one step at a time. By the end you will have parsed a text, read the results, dealt with names that do not resolve, and adjusted the pipeline.

It assumes you have worked through :doc:`installation`, so that you have both the package and a gazetteer. The examples use ``geonames``.

Building a Geoparser
--------------------

A geoparser is made of two modules that you provide explicitly: a **recognizer** that finds place names in text, and a **resolver** that links them to a gazetteer.

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )

Both arguments are required, and there are no defaults: omitting either raises a ``TypeError``. You can pass ``None`` to skip a stage — ``resolver=None`` gives you recognition only — but that has to be said explicitly.

The first time you run this it downloads the models the two modules need, printing something like ``Downloading spaCy model 'en_core_web_sm'...``. That happens once. The modules chosen here are the fast ones, tuned for English and favouring speed over accuracy; :ref:`quickstart-customizing` below covers the alternatives.

Parsing a Text
--------------

Give ``parse()`` a text and it returns a **document**: the text, plus the place names found in it.

.. code-block:: python

   text = (
       "Heavy rain caused flooding across northern England this week. The worst "
       "damage was reported in Manchester and Leeds, where rivers burst their banks "
       "overnight. Emergency services in Sheffield said they had received hundreds "
       "of calls."
   )

   document = geoparser.parse(text)
   print(f"{len(document.toponyms)} toponyms found")

.. code-block:: text

   4 toponyms found

A paragraph rather than a sentence, deliberately. The resolver decides between places of the same name by reading the words around them, so it works markedly better on a few sentences of connected prose than on a lone short sentence — see :ref:`quickstart-context`.

Reading the Results
-------------------

Each toponym knows what it says and where it sits in the text:

.. code-block:: python

   for toponym in document.toponyms:
       print(f"{toponym.text!r} at characters {toponym.start}-{toponym.end}")

.. code-block:: text

   'England' at characters 43-50
   'Manchester' at characters 95-105
   'Leeds' at characters 110-115
   'Sheffield' at characters 181-190

The offsets index into ``document.text``, so ``document.text[toponym.start:toponym.end]`` is the toponym itself, and a wider slice gives you the text around it.

The geographic information is on ``toponym.location``:

.. code-block:: python

   for toponym in document.toponyms:
       location = toponym.location
       print(f"{toponym.text}:")
       print(f"  Name:        {location.data.get('name')}")
       print(f"  Type:        {location.data.get('feature_name')}")
       print(f"  Coordinates: {location.data.get('latitude')}, {location.data.get('longitude')}")

.. code-block:: text

   England:
     Name:        England
     Type:        first-order administrative division
     Coordinates: 52.16045, -0.70312
   Manchester:
     Name:        Manchester
     Type:        seat of a second-order administrative division
     Coordinates: 53.48095, -2.23743
   Leeds:
     Name:        Leeds
     Type:        seat of a second-order administrative division
     Coordinates: 53.79648, -1.54785
   Sheffield:
     Name:        Sheffield
     Type:        seat of a second-order administrative division
     Coordinates: 53.38297, -1.4659

``location`` is a **feature**: one entry in the gazetteer. Its ``data`` is a dictionary of whatever that gazetteer records, which varies between gazetteers and even between sources inside one gazetteer — so read it with ``.get()`` rather than ``data["name"]``.

Note that the gazetteer's name for a place need not be the name in the text. Ask the same pipeline about Vienna and the feature comes back as ``Wien``. If you want to group or count places, use ``location.identifier`` — the gazetteer's stable id for that place, ``2643123`` for Manchester — because names are ambiguous and identifiers are not.

A feature also carries a ``geometry``, a Shapely object you can map or measure:

.. code-block:: python

   point = document.toponyms[1].location.geometry
   print(point, point.x, point.y)

.. code-block:: text

   POINT (-2.23743 53.48095) -2.23743 53.48095

Handling What Is Missing
------------------------

The code above works only because every name resolved and every attribute was present. Neither is guaranteed, so this is the version to actually write:

.. code-block:: python

   text = (
       "The expedition began in Cape Town, where the crew loaded supplies before "
       "heading south. After three weeks at sea they reached South Georgia, a "
       "remote island in the southern Atlantic, and from there they pushed on "
       "toward Antarctica."
   )

   document = geoparser.parse(text)

   for toponym in document.toponyms:
       if toponym.location is None:
           print(f"{toponym.text}: not resolved")
       else:
           print(f"{toponym.text}: {toponym.location.data.get('name')}")

.. code-block:: text

   Cape Town: Cape Town
   South Georgia: not resolved
   Atlantic: Atlantic Ocean
   Antarctica: Antarctica

``location`` is ``None`` when a name was recognized but not resolved, as happened to South Georgia here. There are two reasons this can happen: the place may be absent from the gazetteer, or no candidate may have passed the resolver's similarity threshold. Either way, check for ``None`` before reading attributes.

Individual attributes go missing too, independently of that:

.. code-block:: python

   for toponym in document.toponyms:
       if toponym.location:
           print(f"{toponym.text}: {toponym.location.data.get('country_name')!r}")

.. code-block:: text

   Cape Town: 'South Africa'
   Atlantic: None
   Antarctica: None

An ocean and a continent are in no country, so ``country_name`` is simply absent for them. The same applies to ``geometry``, which is ``None`` for places a gazetteer records by name without locating. Reading attributes with ``.get()``, and checking ``location`` for ``None``, is therefore the normal way to work with results.

Parsing Several Texts
---------------------

``parse()`` accepts a list, and processes it as a batch, which is considerably faster than looping:

.. code-block:: python

   texts = [
       "Researchers in Nairobi and Mombasa collected samples along the Kenyan coast.",
       "The festival moved from Salzburg to Vienna after a dispute over funding.",
       "The conference was held in Zurich, with satellite events in Geneva and Basel.",
   ]

   documents = geoparser.parse(texts)

   for i, document in enumerate(documents, start=1):
       print(f"Document {i}:")
       for toponym in document.toponyms:
           name = toponym.location.data.get("name") if toponym.location else "unresolved"
           print(f"  {toponym.text} -> {name}")

.. code-block:: text

   Document 1:
     Nairobi -> Nairobi
     Mombasa -> Mombasa
   Document 2:
     Salzburg -> Salzburg
     Vienna -> Wien
   Document 3:
     Zurich -> Zürich
     Geneva -> Geneva
     Basel -> Basel

The result mirrors the input: pass a string and you get one document, pass a list and you get a list of documents **in the same order**. That ordering is what lets you relate results back to wherever the texts came from:

.. code-block:: python

   for text, document in zip(texts, documents):
       ...

For larger or longer-lived work, identifiers are a sturdier link than position — see :doc:`guides/projects`.

.. _quickstart-context:

Why Context Matters
-------------------

How much context a text provides has a large effect on the results, and it is worth seeing that directly. Here is a short sentence:

.. code-block:: python

   document = geoparser.parse("She flew from Paris to Tokyo last spring.")

.. code-block:: text

   'Paris'  ->  not resolved
   'Tokyo'  ->  Takeo, Japan

Tokyo has become Takeo, a town in Kyushu, and Paris has not resolved at all. Now the same two names with something around them:

.. code-block:: python

   document = geoparser.parse(
       "She flew from Paris to Tokyo last spring, changing planes twice. The trip "
       "was her first visit to Japan, and she spent a week in the city before "
       "returning to France."
   )

.. code-block:: text

   'Paris'   ->  Paris, France
   'Tokyo'   ->  Tokyo, Japan
   'Japan'   ->  Japan
   'France'  ->  Republic of France

Nothing changed but the surrounding words. The resolver compares the context a name appears in against descriptions of the candidate places, so a name with no context to go on is a name it has little basis to choose for. The recognizer is context-dependent in the same way, and will miss names in a bare sentence that it finds in a paragraph.

The practical consequences:

- **Parse whole paragraphs or documents**, not isolated sentences or bare lists of place names. If your data really is a list of names — a spreadsheet column, say — a geoparser is the wrong tool, and you want a plain gazetteer lookup instead (:doc:`guides/gazetteers`).
- **Check results against the text.** Both errors above are silent: nothing is raised, and ``Takeo`` looks like a plausible answer until you compare it with what the sentence said.
- **The defaults are tuned for English news prose.** That is what the default models were trained on. On historical, literary, or non-English material, expect worse and read the next section.

.. _quickstart-customizing:

Changing the Pipeline
---------------------

Both modules take parameters, which is how you adapt the pipeline to your own material:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       # A larger, more accurate spaCy model
       recognizer=SpacyRecognizer(model_name="en_core_web_trf"),
       # A different gazetteer, and a lower confidence threshold
       resolver=SentenceTransformerResolver(
           gazetteer_name="swissnames3d",
           min_similarity=0.5,
       ),
   )

   document = geoparser.parse("Zurich is the largest city in Switzerland.")

Two parameters have the largest effect on how much gets recognized and resolved:

- ``model_name`` on the recognizer. The default ``en_core_web_sm`` is trained on contemporary English news text. On historical, literary, or non-English material it can miss most place names, and nothing downstream can recover a name that was never found. A larger model, or one for your language, usually helps.
- ``min_similarity`` on the resolver, default ``0.6``. It is how confident the resolver must be before committing. Lower it to resolve more and risk more mistakes; raise it for the opposite. The default is calibrated for English news text against GeoNames, so other material generally wants a lower value.

:doc:`guides/modules` covers every parameter, the second pre-trained resolver model, and how to write modules of your own.

Keeping the Results
-------------------

``parse()`` throws its work away once it returns. To keep it:

.. code-block:: python

   document = geoparser.parse("Berlin is the capital of Germany.", save=True)

.. code-block:: text

   Results saved under project name: a1b2c3d4

The printed name is how you get back to those results later, with ``Project("a1b2c3d4")``. When you know in advance that you want to keep something, it is better to create a project with a name you chose — see :doc:`guides/projects`.

Next Steps
----------

You can now parse text and read the results. The obvious next question is how to get them into something you can analyse:

- :doc:`guides/results` — rows, CSV, pandas, GeoJSON, and how to keep the surrounding context
- :doc:`guides/modules` — if too little is being recognized or resolved, the fix is here
- :doc:`concepts` — the ideas underneath all of this, if you skipped it
- :doc:`api/geoparser` — the full API reference
