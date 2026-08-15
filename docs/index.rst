.. _index:

Irchel Geoparser
================

The **Irchel Geoparser** finds place names in text and links them to places in a geographic database.

Give it a sentence, a document, or a corpus, and it returns the place names it found, each one linked where possible to an entry in a **gazetteer** — a database of places. What that entry tells you depends on the gazetteer, but usually includes coordinates and attributes such as the kind of place it is and the administrative units it belongs to. That turns prose into data you can map, count, and join to anything else.

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
       location = toponym.location  # None if the name could not be resolved
       print(f"{toponym.text} → {location.data['name']}, {location.data['country_name']} "
             f"({location.data['latitude']}, {location.data['longitude']})")

.. code-block:: text

   Zurich → Zürich, Switzerland (47.36667, 8.55)
   Geneva → Geneva, Switzerland (46.20222, 6.14569)
   Basel → Basel, Switzerland (47.55839, 7.57327)

Each name here has been tied to one specific entry in GeoNames, so besides the name and coordinates printed above you also have a stable identifier for the place, what kind of place it is, the administrative units it belongs to, and a geometry you can map, measure, or export.

Start with :doc:`installation`, then parse your first text in the :doc:`quickstart`. The :doc:`demo` maps every place mentioned in Jules Verne's *Around the World in Eighty Days*.

What It Does
------------

Geoparsing is conventionally split into two stages, and this library keeps them separate. A **recognizer** finds which words in a text are place names; a **resolver** then decides which place each name refers to, choosing from the entries of a gazetteer. That second step is the hard one — GeoNames records 122 places called Paris and 291 called Springfield — and it is why installing a gazetteer is part of setting the library up.

You supply the recognizer, the resolver, and the gazetteer explicitly, and each can be exchanged for another. That is the library's central design decision, and most of what the library can do follows from it. A recognizer that finds place names with a statistical model can be replaced by one that takes spans you supply yourself; either module can be pointed at a different underlying model; either can be fine-tuned on your own annotated data for a particular language, period, or domain; and you can write a module of your own against a small interface. Results from several such pipelines can be kept side by side over the same corpus and compared.

The two pre-configured gazetteers cover the modern world and Switzerland in detail, and other geographic data — a historical atlas, an excavation catalogue, a national register, your own field data — becomes a gazetteer through a YAML configuration file, with no code to write.

:doc:`concepts` explains all of this in more depth, and without code.

Project Status
--------------

The library is under active development and its architecture is still evolving; while the version remains below 1.0, minor releases may make breaking changes. `ROADMAP.md <https://github.com/dguzh/geoparser/blob/main/ROADMAP.md>`_ describes the larger changes we intend to make.

Contributing
------------

The Irchel Geoparser is open source. Questions, bug reports, and ideas are all welcome on the `issue tracker <https://github.com/dguzh/geoparser/issues>`_, and contributions are welcome too — see `CONTRIBUTING.md <https://github.com/dguzh/geoparser/blob/main/CONTRIBUTING.md>`_.

Acknowledgments
---------------

The Irchel Geoparser originated as part of Diego Gomes' Master's thesis and was further developed with support from the `Department of Geography <https://www.geo.uzh.ch/>`_ at the University of Zurich and the `Public Data Lab <https://publicdatalab.ch/>`_ of the Digitalization Initiative of the Zurich Higher Education Institutions. We thank Prof. Dr. Ross Purves for the opportunity to continue this work as part of a research project.

License
-------

The Irchel Geoparser is released under the `MIT License <https://github.com/dguzh/geoparser/blob/main/LICENSE>`_. It depends on a number of third-party libraries, listed in `pyproject.toml <https://github.com/dguzh/geoparser/blob/main/pyproject.toml>`_. Each is distributed separately under its own license, which pip installs alongside it.


.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :hidden:

   installation
   quickstart
   concepts
   demo

.. toctree::
   :maxdepth: 1
   :caption: User Guides
   :hidden:

   guides/results
   guides/modules
   guides/gazetteers
   guides/custom-gazetteers
   guides/projects
   guides/annotating
   guides/training

.. toctree::
   :maxdepth: 1
   :caption: API Reference
   :hidden:

   api/geoparser
   api/project
   api/modules
   api/gazetteer
   api/models
