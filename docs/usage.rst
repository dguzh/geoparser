.. _usage:

Usage
=====

This section provides a comprehensive guide on how to use the Geoparser library to recognize and resolve toponyms in unstructured text. You'll learn how to perform geoparsing tasks, customize various components, and train your own models for specific use cases.

Basic Usage
-----------

In this section, we'll walk through the basic steps to get started with Geoparser, including initializing the Geoparser, parsing texts, and accessing the results.

Initializing the Geoparser
~~~~~~~~~~~~~~~~~~~~~~~~~~

To start using Geoparser, import it and create an instance of the ``Geoparser`` class:

.. code-block:: python

   from geoparser import Geoparser

   geoparser = Geoparser()

By default, Geoparser uses the following configuration:

.. code-block:: python

   geoparser = Geoparser(
       spacy_model="en_core_web_sm",
       transformer_model="dguzh/geo-all-MiniLM-L6-v2",
       gazetteer="geonames"
   )

These defaults prioritize speed over accuracy and are optimized for English texts. If you require higher accuracy and don't mind increased computational cost, or need to process texts in other languages, you can specify different models as shown in the `Advanced Usage`_ section.

Performing Geoparsing
~~~~~~~~~~~~~~~~~~~~~

To geoparse texts, use the ``parse`` method of the Geoparser instance which will perform both toponym recognition and resolution. It's important to pass the texts as a list of strings, which enables batch processing and significantly improves efficiency:

.. code-block:: python

   texts = [
       "The Grossmünster is one of the most famous landmarks in Zurich.",
       "From skyscrapers in The Big Apple to auto factories in Motor City, America has it all."
   ]
   
   docs = geoparser.parse(texts)

The ``parse`` method accepts a list of strings and returns a list of ``GeoDoc`` objects, each representing a geoparsed document.

Accessing Location Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After parsing, you can access the toponyms identified in each document through ``GeoDoc.toponyms``, which returns a tuple of ``GeoSpan`` objects representing the toponyms in the document. The resolved location of each toponym can be accessed using ``GeoSpan.location``, which returns a dictionary containing various location attributes sourced from the gazetteer. For example, when using the GeoNames gazetteer, a resolved location might look like this:

.. code-block:: python

   {
       "geonameid": "6946270",
       "name": "Grossmünster",
       "feature_type": "church",
       "latitude": 47.3702,
       "longitude": 8.544,
       "elevation": None,
       "population": 0,
       "admin2_geonameid": "6458798",
       "admin2_name": "Bezirk Zürich",
       "admin1_geonameid": "2657895",
       "admin1_name": "Zurich",
       "country_geonameid": "2658434",
       "country_name": "Switzerland"
   }

Iterate through the toponyms in a document to access the resolved locations:

.. code-block:: python

   for doc in docs:
       print(f"Document: {doc.text}")
       for toponym in doc.toponyms:
           print(f"- Toponym: {toponym.text}")
           location = toponym.location
           if location:
               print(f"  Resolved Location: {location['name']}, {location['country_name']}")
               print(f"  Feature Type: {location['feature_type']}")
               print(f"  Coordinates: ({location['latitude']}, {location['longitude']})")
               print(f"  Score: {toponym.score}")
           else:
               print("Location could not be resolved.")
       print()

When working with large datasets, it is recommended to access location data through the ``doc.locations`` property, which bundles the location retrieval of all toponyms within a document into a single database query:

.. code-block:: python

   for doc in docs:
       print(f"Document: {doc.text}")
       for toponym, location in zip(doc.toponyms, doc.locations):
           print(f"- Toponym: {toponym.text}")
           if location:
               print(f"  Resolved Location: {location['name']}, {location['country_name']}")
               print(f"  Feature Type: {location['feature_type']}")
               print(f"  Coordinates: ({location['latitude']}, {location['longitude']})")
               print(f"  Score: {toponym.score}")
           else:
               print("Location could not be resolved.")
       print()

Example Output:

.. code-block:: text

   Document: The Grossmünster is one of the most famous landmarks in Zurich.
   - Toponym: Grossmünster
     Resolved Location: Grossmünster, Switzerland
     Feature Type: church
     Coordinates: (47.3702, 8.544)
     Score: 0.7381351590156555
   - Toponym: Zurich
     Resolved Location: Zürich, Switzerland
     Feature Type: seat of a first-order administrative division
     Coordinates: (47.36667, 8.55)
     Score: 0.7467491626739502
   
   Document: From skyscrapers in The Big Apple to auto factories in Motor City, America has it all.
   - Toponym: The Big Apple
     Resolved Location: New York City, United States
     Feature Type: populated place
     Coordinates: (40.71427, -74.00597)
     Score: 0.689016580581665
   - Toponym: Motor City
     Resolved Location: Detroit, United States
     Feature Type: seat of a second-order administrative division
     Coordinates: (42.33143, -83.04575)
     Score: 0.8195096254348755
   - Toponym: America
     Resolved Location: United States, United States
     Feature Type: independent political entity
     Coordinates: (39.76, -98.5)
     Score: 0.7686382532119751

If Geoparser was unable to resolve a location, ``toponym.location`` will be ``None``. Always check if ``location`` is valid before accessing its attributes to avoid errors.

The ``toponym.score`` property provides the similarity score between the toponym's context and the resolved location. Higher scores indicate a higher confidence in the prediction. Depending on your specific requirements, you might use this score to set a threshold for which predictions to consider valid.

.. _Advanced Usage:

Advanced Usage
--------------

This section explores advanced features such as utilizing various spaCy and transformer models, sourcing different gazetteers, filtering candidate locations, and leveraging CUDA for acceleration.

Using Different spaCy Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify different spaCy models when initializing Geoparser:

.. code-block:: python

   geoparser = Geoparser(spacy_model="en_core_web_trf")

This is useful if you prefer a larger model for higher toponym recognition accuracy or need support for a different language. Ensure the spaCy model is installed before using it.

Using Different Transformer Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Geoparser provides two pre-trained ``SentenceTransformer`` models fine-tuned for toponym disambiguation:

- **Faster but less accurate**: ``dguzh/geo-all-MiniLM-L6-v2``
- **Slower but more accurate**: ``dguzh/geo-all-distilroberta-v1``

You can specify different transformer models during initialization:

.. code-block:: python

   geoparser = Geoparser(transformer_model="dguzh/geo-all-distilroberta-v1")

These models have been trained using English news articles. Therefore, they are most effective when parsing English texts and when used in combination with an English spaCy model. If you wish to parse texts in other languages, these models may not perform well. In such cases, it is recommended that you train your own custom model, as explained in the `Training a Custom Model`_ section.

Using Different Gazetteers
~~~~~~~~~~~~~~~~~~~~~~~~~~

Geoparser supports multiple gazetteers. Specify a different gazetteer during initialization:

.. code-block:: python

   geoparser = Geoparser(gazetteer="swissnames3d")

Currently supported gazetteers:

- **GeoNames (global)**: ``geonames``
- **SwissNames3D (Switerland)**: ``swissnames3d``

It is possible to configure custom gazetteers. This involves writing a configuration file and a custom Gazetteer subclass to handle specific data formats during the database setup. Detailed instructions for this process will be provided in future documentation.

Filtering Candidate Locations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filters can be applied to restrict candidate locations during the resolution process. This can be useful when you want to constrain geoparsing results to specific regions or types of locations.

For example, restrict candidates to locations in Austria, Germany, and Switzerland:

.. code-block:: python

   filter = {"country_name": ["Austria", "Germany", "Switzerland"]}

   docs = geoparser.parse(texts, filter=filter)

The ``filter`` parameter is a dictionary where keys are attribute names and values are lists of allowed values. Valid attributes depend on the gazetteer used.

Using CUDA for Acceleration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a CUDA-enabled GPU, you can leverage it for faster computations.

Check if CUDA is available:

.. code-block:: python

   import torch

   print(torch.cuda.is_available())

If ``True``, Geoparser will automatically utilize the GPU.

.. _Training a Custom Model:

Training a Custom Model
-----------------------

You can fine-tune a ``SentenceTransformer`` model using ``GeoparserTrainer`` to better suit your specific data or to support other languages.

Preparing the Corpus
~~~~~~~~~~~~~~~~~~~~

Format your training data as a list of dictionaries, each representing a document with its text and toponyms:

.. code-block:: python

   train_corpus = [
       {
           "text": "I traveled from New York to Paris last summer.",
           "toponyms": [
               {
                   "text": "New York",
                   "start": 16,
                   "end": 24,
                   "loc_id": "5128581"
               },
               {
                   "text": "Paris",
                   "start": 28,
                   "end": 33,
                   "loc_id": "2988507"
               }
           ]
       },
       {
           "text": "Zurich is a beautiful city in Switzerland.",
           "toponyms": [
               {
                   "text": "Zurich",
                   "start": 0,
                   "end": 6,
                   "loc_id": "2657896"
               },
               {
                   "text": "Switzerland",
                   "start": 30,
                   "end": 41,
                   "loc_id": "2658434"
               }
           ]
       }
   ]

Alternatively, you can use the Annotator web app to annotate texts and create an annotation file. These are JSON files analogous to the corpus format above. You can launch the Annotator with the following command:

.. code-block:: bash

   python -m geoparser annotator

Documentation and instructions for the Annotator will be provided in the future.

Initializing GeoparserTrainer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Import and initialize ``GeoparserTrainer``:

.. code-block:: python

   from geoparser import GeoparserTrainer

   trainer = GeoparserTrainer(
       spacy_model="en_core_web_trf",
       transformer_model="dguzh/geo-all-distilroberta-v1",
       gazetteer="geonames"
   )

The specified ``spacy_model`` is used for tokenization and to validate the provided annotations when ``annotate`` is called on the corpus. Each annotated toponym is compared with the set of toponyms recognized by spaCy. If it doesn't match any spaCy toponym, the annotation is discarded. This helps ensure the model isn't trained with potentially erroneous annotations. You can disable this matching requirement by setting ``include_unmatched=True`` when calling ``annotate``.

The specified ``transformer_model`` is the one that will be fine-tuned. You have the option to either fine-tune one of the provided models or train a model from scratch. If you choose to fine-tune a pre-trained model that has already been optimized for toponym disambiguation, you can further train it with a subset of your data to potentially improve toponym resolution accuracy for your specific corpus. This is particularly useful if your data is from a different domain than the one on which the models were originally trained. Alternatively, you can train a model from scratch, by training a ``SentenceTransformer`` base model that is suitable for your specific language or task. Suitable base models can be found on HuggingFace, including both `official models <https://huggingface.co/models?library=sentence-transformers&author=sentence-transformers>`_ and those `contributed by the community <https://huggingface.co/models?library=sentence-transformers>`_.

The specified ``gazetteer`` must match the one used as the knowledge source for annotations. Furthermore, trained transformer models are specific to the gazetteers they have been fine-tuned with. This is because models learn to compare toponym contexts with textual representations of locations, which in turn depend on the specific attributes provided by the gazetteer.

Loading Annotations
~~~~~~~~~~~~~~~~~~~

Convert your training corpus into annotated ``GeoDoc`` objects:

.. code-block:: python

   train_docs = trainer.annotate(train_corpus)

Or if you want to load annotations from an Annotator file:

.. code-block:: python

   train_docs = trainer.annotate("path/to/annotations.json")

Training the Model
~~~~~~~~~~~~~~~~~~

Train the model:

.. code-block:: python

   trainer.train(train_docs, output_path="path/to/save/model", epochs=1, batch_size=8)

This fine-tunes the model and saves it to the specified path.

Evaluating the Model
~~~~~~~~~~~~~~~~~~~~

You can evaluate the trained model using an evaluation corpus formatted in the same way as the training corpus.

First, annotate the evaluation corpus:

.. code-block:: python

   eval_corpus = [
       # same structure as the training corpus
   ]

   eval_docs = trainer.annotate(eval_corpus)

Next, use the ``resolve`` method to predict locations for the toponyms in the evaluation documents using the newly trained transformer model:

.. code-block:: python

   eval_docs = trainer.resolve(eval_docs)

Finally, evaluate the model's performance:

.. code-block:: python

   metrics = trainer.evaluate(eval_docs)

   print(metrics)

The ``evaluate`` method compares the predicted locations with the annotated ones and returns the following evaluation metrics:

- **Accuracy**: The proportion of toponyms correctly resolved to the exact location entity.
- **Accuracy@161km**: The proportion of toponyms resolved within 161 km (100 miles) of the correct location .
- **MeanErrorDistance**: The average distance in kilometers between the predicted and correct locations.
- **AreaUnderTheCurve**: A metric considering the distribution of error distances (lower is better).

These metrics provide insights into how well the model is performing and can help you adjust your training process accordingly.

Using the Custom Model
~~~~~~~~~~~~~~~~~~~~~~

Use your custom model with Geoparser:

.. code-block:: python

   geoparser = Geoparser(transformer_model="path/to/save/model")
