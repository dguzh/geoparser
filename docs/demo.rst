.. _demo:

Demo
====

Every populated place mentioned in Jules Verne's *Around the World in Eighty Days*, extracted from the novel and mapped — 27 of them, across all 37 chapters. Marker size is how often the place is mentioned; hover over one to read the passages it appears in.

.. raw:: html

   <iframe src="_static/map.html" width="100%" height="550" frameborder="0"></iframe>

The book is from `Project Gutenberg <https://www.gutenberg.org/ebooks/103>`_, and the whole thing runs on the library as documented. The parts that concern geoparsing are walked through below; the rest is downloading the book, splitting it into chapters, and drawing the map.

What the Pipeline Does Here
---------------------------

The novel is split into its 37 chapters, each chapter parsed as one document, and the resolved places aggregated across all of them. Two choices matter, and both differ from the defaults:

.. code-block:: python

   from geoparser import Geoparser
   from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

   # A transformer model finds more place names in literary prose
   recognizer = SpacyRecognizer(model_name="en_core_web_trf")

   # A higher threshold: precision matters more than recall on a map
   resolver = SentenceTransformerResolver(min_similarity=0.7)

   geoparser = Geoparser(recognizer=recognizer, resolver=resolver)

``en_core_web_trf`` rather than the default ``en_core_web_sm``, because nineteenth-century narrative prose is unlike the news text the small model was trained on and it misses noticeably more. And ``min_similarity=0.7`` rather than ``0.6``, because a wrong marker on a map is more damaging than a missing one: a mistake is visible and misleading, while an omission is merely absent. The gazetteer is not named here because ``SentenceTransformerResolver`` uses GeoNames unless told otherwise.

This is the general shape of tuning a pipeline: the defaults are a reasonable starting point, and the right values depend on your material and on which kind of error costs you more.

Parsing and Aggregating
-----------------------

Each chapter goes in as a document, and the results come back in the same order:

.. code-block:: python

   chapter_texts = [chapter["text"] for chapter in chapters]
   documents = geoparser.parse(chapter_texts)

Then the mentions are grouped by the place they resolved to. Two details in this step are worth copying:

.. code-block:: python

   from collections import defaultdict

   places = defaultdict(lambda: {"location": None, "mentions": [], "count": 0})

   for document, chapter in zip(documents, chapters):
       for toponym in document.toponyms:
           if toponym.location is None:
               continue

           # Populated places only — skip regions, seas, and mountains
           if toponym.location.data.get("feature_class") != "P":
               continue

           # Group by identifier, never by name
           entry = places[toponym.location.identifier]
           entry["location"] = toponym.location
           entry["count"] += 1

           # Keep the surrounding text, for the hover popups
           start = max(0, toponym.start - 30)
           end = min(len(document.text), toponym.end + 30)
           entry["mentions"].append((chapter["number"], document.text[start:end]))

**Grouping by** ``identifier``, **not by name**, is the important one. Names are shared between genuinely different places — GeoNames has 122 called Paris — so grouping by ``data["name"]`` would merge distinct places into a single marker.

**Filtering on** ``feature_class`` is what keeps the map readable. GeoNames classifies every feature, and ``"P"`` means a populated place; without the filter, "Europe", "the Atlantic", and "the Rocky Mountains" all become single points, which is misleading rather than informative. The full list of classes is in :doc:`guides/gazetteers`.

Keeping the character offsets is what makes the popups possible. The library gives you positions into the original text, so the passage around each mention costs one slice.

From there it is an ordinary plot: read ``latitude`` and ``longitude`` from each feature's ``data``, size the markers by ``count``, and hand it to a plotting library. The notebook uses Plotly.

Run It Yourself
---------------

The complete notebook is in the repository at `demo/demo.ipynb <https://github.com/dguzh/geoparser/blob/main/demo/demo.ipynb>`_. It downloads the book, splits the chapters, runs the pipeline, and builds the map you see above.

To run it in your own environment, you need the library and the ``geonames`` gazetteer, both covered in :doc:`installation`, plus two extras:

.. code-block:: bash

   pip install jupyter plotly

.. code-block:: bash

   python -m geoparser install geonames

.. code-block:: bash

   jupyter lab demo/demo.ipynb

Expect the parse to take a few minutes: the transformer recognizer is slow on CPU, and there are 37 chapters. A GPU makes a substantial difference — see :ref:`Using a GPU <installation>`.

Alternatively, a pre-built Docker image has everything including the gazetteer already installed:

.. code-block:: bash

   docker run -p 8888:8888 dguzh/geoparser-demo:latest

Then open ``http://localhost:8888`` and run ``demo.ipynb``. The image is convenient but large — around 10 GB compressed, expanding to roughly 30 GB, mostly the GeoNames gazetteer — so the first pull takes a while. Later runs start immediately.
