.. _demo:

Demo
====

See what you can do with the Irchel Geoparser by exploring an interactive map of Jules Verne's `"Around the World in Eighty Days" <https://www.gutenberg.org/ebooks/103>`_. This demo illustrates how you can extract and map place names mentioned throughout the novel, visualizing Phileas Fogg's journey around the world.

.. raw:: html

   <iframe src="_static/map.html" width="100%" height="550" frameborder="0"></iframe>

Try It Yourself
---------------

Want to see how this map was created? You can run the complete demo yourself using a pre-built Docker image.

Install `Docker Desktop <https://www.docker.com/products/docker-desktop>`_, then run this command:

.. code-block:: bash

   docker run -p 8888:8888 dguzh/geoparser-demo:latest

**Note**: The first time you run this, it will take approximately 5 minutes to download the Docker image (compressed to ~10 GB, expands to ~30 GB). Subsequent runs will be instant.

Once started, open your browser to ``http://localhost:8888`` and open the ``demo.ipynb`` notebook. Run all cells to see the complete geoparsing and mapping pipeline in action.

Next Steps
----------

If this demo has sparked your interest:

- :doc:`installation` - Set up the library on your system
- :doc:`quickstart` - Learn the basics of using the geoparser
