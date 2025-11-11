.. _training:

Training
========

This guide explains how to train and fine-tune modules on annotated data to improve performance for specific domains, languages, or use cases.

Overview
--------

The Irchel Geoparser supports training and fine-tuning of modules using annotated data. Any module that implements a ``fit()`` method with the appropriate interface can be trained. Training improves performance on texts that differ from the data the models were originally trained on, and it enables support for new languages or specialized geographic contexts.

The built-in ``SpacyRecognizer`` and ``SentenceTransformerResolver`` modules implement a ``fit()`` method that trains the underlying models on annotated examples. The training process requires documents with ground-truth annotations: for recognizers, you need the positions of place names in text; for resolvers, you need both the place name positions and their correct linkages to gazetteer entries. Training is performed through the project-level methods (``project.train_recognizer()`` and ``project.train_resolver()``), which automatically gather training data from annotated documents in the project and call the module's ``fit()`` method.

Training SpacyRecognizer
------------------------

The ``SpacyRecognizer`` uses spaCy's named entity recognition framework. Training involves fine-tuning an existing spaCy model to better recognize place names in your specific domain or language.

Preparing Training Data
~~~~~~~~~~~~~~~~~~~~~~~

Training data consists of texts and the positions of place names within those texts. You can create annotations manually or load them from files:

.. code-block:: python

   from geoparser import Project

   project = Project("training_corpus")
   
   # Option 1: Create annotations manually
   project.create_references(
       texts=["The summit was held in Geneva."],
       references=[[(26, 32)]],  # Position of "Geneva"
       tag="training"
   )
   
   # Option 2: Load from JSON file
   project.load_annotations(
       path="annotations.json",
       tag="training",
       create_documents=True
   )

See the :doc:`projects` guide for detailed information on working with annotations.

Training the Recognizer
~~~~~~~~~~~~~~~~~~~~~~~

Once you have annotated documents in a project, training a recognizer is straightforward:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer

   project = Project("training_corpus")

   # Create the recognizer to train
   recognizer = SpacyRecognizer(model_name="en_core_web_sm")

   # Train on documents tagged as "gold"
   project.train_recognizer(
       recognizer,
       tag="gold",
       output_path="models/trained_recognizer",
       epochs=10,
       batch_size=8,
       dropout=0.1,
       learning_rate=0.001
   )

The ``train_recognizer()`` method retrieves all documents from the project that have reference annotations associated with the specified tag. It extracts the texts and reference positions, then calls the recognizer's ``fit()`` method to perform the actual training. The trained model is saved to the specified output path.

The training parameters control how the model learns. The ``epochs`` parameter determines how many times the training algorithm iterates over the dataset. More epochs can improve performance but may lead to overfitting if you have limited training data. The ``batch_size`` controls how many examples are processed together during each training step. Larger batches provide more stable gradients but require more memory. The ``dropout`` rate adds regularization by randomly dropping neural network connections during training, which helps prevent overfitting. The ``learning_rate`` determines how quickly the model adjusts its parameters during training.

Using the Trained Model
~~~~~~~~~~~~~~~~~~~~~~~

After training, you can use the trained model by specifying its path when creating a recognizer:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer

   # Load the trained model
   recognizer = SpacyRecognizer(model_name="models/trained_recognizer")

   project = Project("evaluation_corpus")
   project.run_recognizer(recognizer)

The trained recognizer can be used in any workflow just like the pre-trained models. The model path becomes part of the recognizer's configuration, so results from the trained model are tracked separately from results from the base model.

Training SentenceTransformerResolver
-------------------------------------

The ``SentenceTransformerResolver`` uses a SentenceTransformer model to compute embeddings of contexts and location descriptions. Training fine-tunes this model to better capture the semantic relationships between how places are mentioned in your texts and how they should be described for disambiguation.

Preparing Training Data
~~~~~~~~~~~~~~~~~~~~~~~

Training a resolver requires both the positions of place names and their correct resolutions. Each place name must be linked to a specific feature in the gazetteer:

.. code-block:: python

   from geoparser import Project

   project = Project("training_corpus")
   
   # Option 1: Create annotations manually
   project.create_referents(
       texts=["The summit was held in Geneva."],
       references=[[(26, 32)]],
       referents=[[("geonames", "2660645")]],  # Geneva, Switzerland
       tag="training"
   )
   
   # Option 2: Load from JSON file
   project.load_annotations(
       path="annotations.json",
       tag="training",
       create_documents=True
   )

See the :doc:`projects` guide for detailed information on working with annotations.

Training the Resolver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Training a resolver through a project is similar to training a recognizer:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SentenceTransformerResolver

   project = Project("training_corpus")

   # Create the resolver to train
   resolver = SentenceTransformerResolver(
       model_name="dguzh/geo-all-MiniLM-L6-v2",
       gazetteer_name="geonames"
   )

   # Train on documents tagged as "gold"
   project.train_resolver(
       resolver,
       tag="gold",
       output_path="models/trained_resolver",
       epochs=1,
       batch_size=8,
       learning_rate=2e-5,
       warmup_ratio=0.1
   )

The ``train_resolver()`` method retrieves documents with both reference and referent annotations. For each reference that has a referent, it extracts the context, generates candidate descriptions from the gazetteer, and creates training examples that teach the model which candidate description matches the context.

The training parameters differ slightly from the recognizer. Transformer models typically require fewer epochs—often a single epoch is sufficient for fine-tuning. The ``learning_rate`` is usually set quite low (2e-5 is a common default) to avoid destroying the knowledge the model already has. The ``warmup_ratio`` controls how gradually the learning rate increases from zero at the start of training, which helps stabilize the training process.

Using the Trained Model
~~~~~~~~~~~~~~~~~~~~~~~

After training, use the trained resolver by specifying its path:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   recognizer = SpacyRecognizer()
   resolver = SentenceTransformerResolver(
       model_name="models/trained_resolver",
       gazetteer_name="geonames"
   )

   project = Project("evaluation_corpus")
   project.run_recognizer(recognizer)
   project.run_resolver(resolver)

Remember that trained transformer models are specific to the gazetteer they were trained with. A model trained with GeoNames will not work well with SwissNames3D because the location descriptions will have different formats and attributes. If you need to support multiple gazetteers, train separate models for each one.

Evaluation
----------

After training, you should evaluate your models on held-out test data that wasn't used during training. Create a separate project with test annotations and run your trained modules on it:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   # Load test data
   test_project = Project("test_corpus")
   test_project.load_annotations(
       path="test_annotations.json",
       tag="gold",
       create_documents=True
   )

   # Run trained modules
   recognizer = SpacyRecognizer(model_name="models/trained_recognizer")
   resolver = SentenceTransformerResolver(model_name="models/trained_resolver")

   test_project.run_recognizer(recognizer, tag="predicted")
   test_project.run_resolver(resolver, tag="predicted")

   # Retrieve both gold and predicted results for comparison
   gold_docs = test_project.get_documents(tag="gold")
   pred_docs = test_project.get_documents(tag="predicted")

   # Calculate evaluation metrics
   # (You'll need to implement your own comparison logic)
   gold_count = sum(len(doc.toponyms) for doc in gold_docs)
   pred_count = sum(len(doc.toponyms) for doc in pred_docs)
   
   print(f"Gold standard: {gold_count} toponyms")
   print(f"Predictions: {pred_count} toponyms")

For more sophisticated evaluation, you'll want to compute precision, recall, and F1 scores for recognition, and accuracy metrics for resolution. The comparison requires aligning predicted toponyms with gold standard annotations based on position and then checking whether the resolved locations match.

Next Steps
----------

Now that you understand training, you can explore:

- :doc:`modules` - Learn more about the module architecture and creating custom modules
- :doc:`gazetteers` - Understand the geographic databases used for resolution
- :doc:`projects` - Use projects to organize training and evaluation workflows

For complete API documentation of training methods, see the :doc:`../api/project` and :doc:`../api/modules` references.

