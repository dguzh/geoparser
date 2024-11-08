Usage
=====

This guide provides examples of how to use Geoparser to parse texts and access location information.

Instantiate the Geoparser
-------------------------

First, import the `Geoparser` class and create an instance:

.. code-block:: python

   from geoparser import Geoparser

   # Instantiate the Geoparser with default settings
   geoparser = Geoparser()

You can customize the spaCy model, transformer model, and gazetteer:

.. code-block:: python

   geoparser = Geoparser(
       spacy_model="en_core_web_trf",
       transformer_model="dguzh/geo-all-distilroberta-v1",
       gazetteer="geonames"
   )

Parse Texts
-----------

Use the `parse` method to geoparse a list of texts:

.. code-block:: python

   texts = [
       "I visited Zurich last summer.",
       "The Grossmünster is one of the most famous landmarks in Zurich."
   ]

   docs = geoparser.parse(texts)

Access Parsed Location Information
----------------------------------

Each item in `docs` is a `GeoDoc` object containing the parsed information.

Iterate over the documents and access toponyms and their resolved locations:

.. code-block:: python

   for doc in docs:
       print(f"Text: {doc.text}\n")
       for toponym in doc.toponyms:
           print(f"Toponym: {toponym.text}")
           location = toponym.location
           if location:
               print(f"Resolved Location ID: {toponym._.loc_id}")
               print(f"Name: {location['name']}")
               print(f"Feature Type: {location['feature_type']}")
               print(f"Latitude: {location['latitude']}")
               print(f"Longitude: {location['longitude']}\n")
           else:
               print("Location could not be resolved.\n")

Example Output:

.. code-block:: text

   Text: I visited Zurich last summer.

   Toponym: Zurich
   Resolved Location ID: 2657896
   Name: Zürich
   Feature Type: seat of a first-order administrative division
   Latitude: 47.36667
   Longitude: 8.55

   Text: The Grossmünster is one of the most famous landmarks in Zurich.

   Toponym: Grossmünster
   Resolved Location ID: 6946270
   Name: Grossmünster
   Feature Type: church
   Latitude: 47.3702
   Longitude: 8.544

   Toponym: Zurich
   Resolved Location ID: 2657896
   Name: Zürich
   Feature Type: seat of a first-order administrative division
   Latitude: 47.36667
   Longitude: 8.55

Training a Custom Model
-----------------------

If you need to fine-tune the model for specific domains or languages, you can use the `GeoparserTrainer` module.

.. code-block:: python

   from geoparser import GeoparserTrainer

   trainer = GeoparserTrainer()

   # Prepare your annotated corpus and train the model
   trainer.train(train_docs, output_path="path/to/save/model", epochs=3, batch_size=16)
