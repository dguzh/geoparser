.. _index:

Irchel Geoparser
================

The **Irchel Geoparser** is a Python library for geoparsing unstructured text—identifying place names (toponyms) and linking them to their geographic locations. Built on a modular architecture, it provides both simple interfaces for quick tasks and powerful project-based workflows for research and production use.

Overview
--------

Geoparsing involves two fundamental tasks. First, toponym recognition identifies place names within text. Second, toponym resolution disambiguates these names by linking them to specific geographic entities in a gazetteer database. The Irchel Geoparser addresses both tasks through a flexible, extensible framework that combines state-of-the-art language models with efficient search algorithms.

The library has evolved from an integrated prototype into a modular platform. Rather than providing a single fixed pipeline, it offers composable components that can be mixed and matched to create customized geoparsing workflows. This architecture enables researchers to experiment with different recognition and resolution strategies, compare results systematically, and extend the system with their own processing modules without modifying the core codebase.

Key Features
------------

The modular architecture provides several capabilities that distinguish this library from traditional geoparsing tools. Projects offer persistent workspaces where documents and processing results are stored in a local database, enabling long-term research workflows and comparative analysis. For quick tasks, a simple stateless interface creates temporary projects behind the scenes and returns results immediately.

Processing modules implement pluggable recognizers and resolvers that can be easily swapped and combined. The library includes recognizers built on spaCy's named entity recognition and resolvers using fine-tuned SentenceTransformer models for context-aware disambiguation. Users can implement custom modules by adhering to simple interfaces, and these modules integrate seamlessly with the rest of the system. Both built-in and custom modules support training and fine-tuning on annotated data.

The gazetteer system supports multiple geographic databases through configuration files rather than hardcoded logic. Built-in support includes GeoNames for global coverage and SwissNames3D for Switzerland. The configuration-driven installer automatically generates optimized database schemas and provides multiple search strategies—from exact string matching to fuzzy search—that resolvers can employ based on their disambiguation approach.

Getting Started
---------------

To begin using the Irchel Geoparser, follow the :doc:`installation` guide to set up the library, download required models, and install a gazetteer. Then proceed to the :doc:`quickstart` guide for a simple example of parsing text and accessing results.

For more advanced usage, explore the user guides that cover project-based workflows, working with different modules, training your own models, and configuring gazetteers. The API reference provides detailed documentation of all classes and methods.

Contributing
------------

The Irchel Geoparser is an open-source project, and contributions are welcome. If you encounter issues or have suggestions for improvements, please open an issue or submit a pull request on the `GitHub repository <https://github.com/dguzh/geoparser>`_.

Acknowledgments
---------------

The Irchel Geoparser originated as part of my Master's thesis and was further developed with support from the `Department of Geography <https://www.geo.uzh.ch/>`_ at the University of Zurich. I thank my supervisor, Prof. Dr. Ross Purves, for his insightful feedback, encouragement, and the opportunity to continue this work as part of a research project.

License
-------

The Irchel Geoparser is released under the `MIT License <https://github.com/dguzh/geoparser/blob/main/LICENSE>`_. It also uses several third-party libraries, each with its own license. For a complete list of these licenses, see the `full license details <https://github.com/dguzh/geoparser/blob/main/THIRD_PARTY_LICENSES>`_ in the repository.


.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :hidden:

   installation
   quickstart

.. toctree::
   :maxdepth: 1
   :caption: User Guides
   :hidden:

   guides/working_with_projects
   guides/modules
   guides/training
   guides/gazetteers

.. toctree::
   :maxdepth: 1
   :caption: API Reference
   :hidden:

   api/geoparser
   api/project
   api/modules
   api/gazetteer
   api/models
