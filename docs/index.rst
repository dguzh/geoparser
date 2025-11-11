.. _index:

Irchel Geoparser
================

The **Irchel Geoparser** is a Python library for identifying place names in unstructured text and linking them to geographic locations. It provides a modular platform for geoparsing that supports custom processing strategies, persistent project-based workflows, and configuration-driven gazetteer integration.

Overview
--------

Geoparsing extracts place names from text and links them to geographic locations. The Irchel Geoparser approaches this task through a two-stage pipeline that separates toponym recognition (identifying place names) from toponym resolution (linking them to specific locations). This separation is a deliberate design choice that enables flexible experimentation with different processing strategies and systematic comparison of their performance. Identified toponyms are linked to gazetteer databases that provide rich geographic metadata including coordinates, administrative hierarchies, feature types, and population information.

Key Features
------------

- **Modular Architecture**: Pluggable recognizer and resolver modules can be mixed, matched, and extended by implementing well-defined interfaces
- **Project-Based Workflows**: Documents and processing results are stored in a persistent database, enabling long-term research and comparative analysis
- **Configuration Tracking**: Modules are tracked by their configuration to avoid redundant processing and support side-by-side comparison of different strategies
- **Custom Gazetteers**: Arbitrary geographic databases can be integrated through YAML configuration files that describe data sources and transformations
- **Automatic Setup**: The system handles gazetteer downloading, schema generation, data transformation, indexing, and spatial operations automatically
- **Trainable Modules**: Built-in recognizers and resolvers can be fine-tuned on annotated data to improve performance for specific domains or languages

Getting Started
---------------

To begin using the Irchel Geoparser, follow the :doc:`installation` guide to set up the library and install a gazetteer. Then proceed to the :doc:`quickstart` guide for a simple example of parsing text and accessing results.

For more advanced usage, explore the user guides that cover :doc:`guides/projects`, :doc:`guides/modules`, :doc:`guides/training`, and :doc:`guides/gazetteers`. The API reference provides detailed documentation of all classes and methods.

Contributing
------------

The Irchel Geoparser is an open-source project, and contributions are welcome. If you encounter issues or have suggestions for improvements, please open an issue or submit a pull request on the `GitHub repository <https://github.com/dguzh/geoparser>`_.

Acknowledgments
---------------

The Irchel Geoparser originated as part of my Master's thesis and was further developed with support from the `Department of Geography <https://www.geo.uzh.ch/>`_ at the University of Zurich and the `Public Data Lab <https://publicdatalab.ch/>`_ of the Digitalization Initiative of the Zurich Higher Education Institutions. I thank Prof. Dr. Ross Purves for the opportunity to continue this work as part of a research project.

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

   guides/projects
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
