.. _quickstart:

Quickstart
==========

This guide provides a quick introduction to using the Irchel Geoparser for basic geoparsing tasks. After following the :doc:`installation` guide, you can start parsing text with just a few lines of code.

Basic Usage
-----------

The simplest way to use the library is through the ``Geoparser`` class, which provides a stateless interface for quick geoparsing tasks. A geoparser is built from two modules that you provide explicitly: a recognizer that finds place names, and a resolver that links them to a gazetteer. The modules used below are optimized for English texts, prioritizing speed over accuracy. See the :ref:`customizing-geoparser` section for other options.

Here's a minimal working example, which assumes the ``geonames`` gazetteer has been installed as described in the :doc:`installation` guide:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   # Initialize the geoparser with a recognizer and a resolver
   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )

   # Parse a text
   text = "The Eiffel Tower in Paris attracts millions of visitors each year."
   document = geoparser.parse(text)

   # Access the results
   print(f"Document: {document.text}\n")
   for toponym in document.toponyms:
       print(f"  Toponym: {toponym.text}")
       if toponym.location:
           location = toponym.location
           print(f"    Name: {location.data.get('name')}")
           print(f"    Country: {location.data.get('country_name')}")
           print(f"    Coordinates: ({location.data.get('latitude')}, {location.data.get('longitude')})")
       else:
           print("    Location: Could not be resolved")
       print()

This code identifies place names in the text and links them to geographic locations in the GeoNames gazetteer. The output might look like:

.. code-block:: text

   Document: The Eiffel Tower in Paris attracts millions of visitors each year.

     Toponym: Eiffel Tower
       Name: Eiffel Tower
       Country: France
       Coordinates: (48.85837, 2.29448)

     Toponym: Paris
       Name: Paris
       Country: France
       Coordinates: (48.85341, 2.3488)

Processing Multiple Documents
------------------------------

The ``parse()`` method accepts a list of texts as well as a single text string, and the result mirrors what was passed in: a single text is parsed into a single ``Document``, while a list of texts is parsed into a list of ``Document`` objects. Processing multiple documents together enables efficient batch processing:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )

   texts = [
       "London is the capital of the United Kingdom.",
       "Tokyo is Japan's largest city.",
       "The Statue of Liberty stands in New York Harbor."
   ]

   documents = geoparser.parse(texts)

   for i, doc in enumerate(documents, 1):
       print(f"Document {i}:")
       for toponym in doc.toponyms:
           if toponym.location:
               print(f"  - {toponym.text} → {toponym.location.data.get('name')}")
       print()

Understanding the Results
--------------------------

A single text is parsed into a single ``Document``, which the first example above works with directly. A list of texts is parsed into a list of ``Document`` objects in the same order as the input texts, so results can be related back to whatever the texts came from. Either way, each document has a ``toponyms`` property that provides access to the identified place names (references) within that document.

Each toponym (``Reference`` object) has several important properties:

- ``text``: The actual text of the place name as it appears in the document
- ``start``: The starting character position in the document text
- ``end``: The ending character position in the document text
- ``location``: The resolved geographic entity (a ``Feature`` object), or ``None`` if the toponym is unresolved

When a toponym is successfully resolved, its ``location`` property contains a ``Feature`` object with geographic information. The feature has two main properties:

- ``data``: A dictionary containing attributes from the gazetteer. For GeoNames, common attributes include ``name``, ``country_name``, ``latitude``, ``longitude``, ``population``, ``feature_name`` (the type of place), and various administrative divisions.
- ``geometry``: A Shapely geometry object representing the feature's spatial extent (typically a Point for most gazetteers, but can be polygons or other geometry types).

Working with Unresolved Toponyms
---------------------------------

Not all identified place names can be successfully linked to geographic locations. Always check if the location is ``None`` before accessing its attributes:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )
   document = geoparser.parse("They traveled from Atlantis to Wonderland.")

   for toponym in document.toponyms:
       print(f"Toponym: {toponym.text}")
       if toponym.location:
           print(f"  Resolved to: {toponym.location.data.get('name')}")
       else:
           print("  Could not be resolved (fictional location)")

.. _customizing-geoparser:

Customizing the Geoparser
--------------------------

The examples above use ``SpacyRecognizer`` and ``SentenceTransformerResolver`` with their default settings. Both modules take parameters of their own, so a geoparser can be tailored to the language, domain, and gazetteer you work with:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   # Use a more accurate spaCy model
   recognizer = SpacyRecognizer(model_name="en_core_web_trf")
   
   # Use a different gazetteer
   resolver = SentenceTransformerResolver(gazetteer_name="swissnames3d")

   geoparser = Geoparser(recognizer=recognizer, resolver=resolver)
   
   document = geoparser.parse("Zurich is the largest city in Switzerland.")

For more details on working with different modules, see the :doc:`guides/modules` guide.

Persisting Results
------------------

By default, the ``parse()`` method creates a temporary project internally and deletes it after returning the results. If you want to keep the results for later analysis, use the ``save=True`` parameter:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   geoparser = Geoparser(
       recognizer=SpacyRecognizer(),
       resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
   )
   document = geoparser.parse("Berlin is the capital of Germany.", save=True)
   # Results saved under project name: a1b2c3d4

When ``save=True``, the method prints the project name that was created. You can later access these results using the ``Project`` class, as described in the :doc:`guides/projects` guide.

Next Steps
----------

This quickstart covered the basics of using the Irchel Geoparser for simple tasks. To learn more about advanced features, explore these guides:

- :doc:`guides/projects` - Persistent workspaces for research and analysis
- :doc:`guides/modules` - Using and creating custom recognizers and resolvers
- :doc:`guides/training` - Fine-tuning models on your own data
- :doc:`guides/gazetteers` - Working with different geographic databases

For complete API documentation, see the :doc:`api/geoparser` reference.

