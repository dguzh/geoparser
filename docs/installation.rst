Installation
============

This guide will help you install and set up Geoparser on your system.

Install Geoparser
-----------------

You can install Geoparser using `pip`:

.. code-block:: bash

   pip install geoparser

Install spaCy Models
--------------------

Geoparser uses spaCy for toponym recognition. You need to download a spaCy model that suits your needs. For example, to download the English transformer model:

.. code-block:: bash

   python -m spacy download en_core_web_trf

You can choose other spaCy models or languages as required.

Set Up Gazetteer Database
-------------------------

Geoparser requires a gazetteer database for toponym resolution. By default, it uses the GeoNames gazetteer. You can set it up using the following command:

.. code-block:: bash

   python -m geoparser download geonames

This will download and set up the GeoNames database locally.
