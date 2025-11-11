.. _training:

Training and Fine-tuning
=========================

The Irchel Geoparser supports training and fine-tuning of modules using annotated data. This capability allows you to adapt the built-in recognizers and resolvers to your specific domain, language, or use case. Training improves performance on texts that differ from the data the models were originally trained on, and it enables support for new languages or specialized geographic contexts.

Overview
--------

Both the ``SpacyRecognizer`` and ``SentenceTransformerResolver`` implement a ``fit()`` method that trains the underlying models on annotated examples. The training process requires documents with ground-truth annotations: for recognizers, you need the positions of place names in text; for resolvers, you need both the place name positions and their correct linkages to gazetteer entries.

The library provides two approaches for training. You can use the project-level training methods (``project.train_recognizer()`` and ``project.train_resolver()``), which automatically gather training data from annotated documents in the project. Alternatively, you can call the module's ``fit()`` method directly, providing the training data as Python lists. Both approaches produce the same trained models, but the project-level methods are more convenient when working with annotations stored in the database.

Training SpacyRecognizer
------------------------

The ``SpacyRecognizer`` uses spaCy's named entity recognition framework. Training involves fine-tuning an existing spaCy model to better recognize place names in your specific domain or language.

Preparing Training Data
~~~~~~~~~~~~~~~~~~~~~~~

Training data consists of texts and the positions of place names within those texts. You can prepare this data manually or load it from annotation files:

.. code-block:: python

   from geoparser import Project

   project = Project("training_corpus")

   # Load annotations from a JSON file
   project.load_annotations(
       path="annotated_news.json",
       tag="gold",
       create_documents=True
   )

The annotation file should contain documents with their texts and toponyms marked with start and end positions. The library's annotator tool can help create these annotations, or you can prepare them in any tool that exports to the required JSON format.

Using Project-Level Training
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Using Direct Training
~~~~~~~~~~~~~~~~~~~~~

If you have training data as Python lists rather than in a project, you can train directly:

.. code-block:: python

   from geoparser.modules import SpacyRecognizer

   # Training data: texts and reference positions
   texts = [
       "The conference was held in Geneva.",
       "Delegates from Paris and Berlin attended.",
       "The next meeting will be in Vienna."
   ]

   references = [
       [(27, 33)],  # "Geneva"
       [(15, 20), (25, 31)],  # "Paris" and "Berlin"
       [(30, 36)]  # "Vienna"
   ]

   # Train the recognizer
   recognizer = SpacyRecognizer(model_name="en_core_web_sm")
   recognizer.fit(
       texts,
       references,
       output_path="models/trained_recognizer",
       epochs=10,
       batch_size=8
   )

The ``fit()`` method accepts the same training parameters as the project-level method. Make sure the reference positions are accurate character offsets in the texts, as incorrect positions will lead to poor training results.

Label Distillation
~~~~~~~~~~~~~~~~~~

The SpacyRecognizer uses a label distillation approach during training. Instead of assigning a fixed label (like "LOC" or "GPE") to all training examples, it processes each annotation with the base model to determine which specific entity type that model would have assigned. This approach preserves the entity type distinctions that spaCy learned during its original training, resulting in a model that maintains good performance across different types of geographic entities.

You don't need to provide entity type labels in your training data—the distillation process handles this automatically. Simply mark the positions of place names, and the training procedure will determine appropriate labels based on the context and the base model's predictions.

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

Training a resolver requires not just the positions of place names but also their correct resolutions. Each place name must be linked to a specific feature in the gazetteer using its identifier:

.. code-block:: python

   from geoparser import Project

   project = Project("training_corpus")

   # Load annotations with both references and referents
   project.load_annotations(
       path="annotated_news.json",
       tag="gold",
       create_documents=True
   )

The annotation file must include ``loc_id`` fields for each toponym, specifying which gazetteer feature that toponym refers to. Empty or null ``loc_id`` values indicate toponyms that should not be included in training (for example, fictional places or toponyms the annotator could not confidently resolve).

Using Project-Level Training
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

Using Direct Training
~~~~~~~~~~~~~~~~~~~~~

You can also train a resolver directly with Python lists:

.. code-block:: python

   from geoparser.modules import SentenceTransformerResolver

   # Training data: texts, reference positions, and referents
   texts = [
       "The conference was held in Geneva.",
       "Delegates from Paris and Berlin attended."
   ]

   references = [
       [(27, 33)],  # "Geneva"
       [(15, 20), (25, 31)]  # "Paris" and "Berlin"
   ]

   referents = [
       [("geonames", "2660645")],  # Geneva, Switzerland
       [("geonames", "2988507"), ("geonames", "2950159")]  # Paris, France and Berlin, Germany
   ]

   # Train the resolver
   resolver = SentenceTransformerResolver(gazetteer_name="geonames")
   resolver.fit(
       texts,
       references,
       referents,
       output_path="models/trained_resolver",
       epochs=1,
       batch_size=8
   )

The referents must be tuples of ``(gazetteer_name, identifier)`` where the identifier corresponds to the location_id_value in the gazetteer. Make sure these identifiers exist in the gazetteer before training, as the training process will query the gazetteer to generate location descriptions.

Contrastive Learning
~~~~~~~~~~~~~~~~~~~~~

The resolver uses ContrastiveLoss for training, which teaches the model to assign high similarity scores to correct context-description pairs and low scores to incorrect pairs. For each training example, the system retrieves all candidates that match the place name from the gazetteer. The correct candidate (specified by the referent annotation) serves as a positive example, while the other candidates serve as negative examples. This approach helps the model learn to distinguish between similar locations based on context.

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

Best Practices
--------------

Several practices will help you achieve good results when training modules. First, ensure you have sufficient training data—at least several hundred annotated examples for recognizers and ideally over a thousand for resolvers. More data generally leads to better performance, especially for resolvers which need to learn fine-grained distinctions between similar locations.

Split your annotated data into training, validation, and test sets. Use the training set for fitting the model, the validation set for tuning hyperparameters like learning rates and dropout, and the test set only for final evaluation. This prevents overfitting and gives you an honest assessment of how the model will perform on new data.

When annotating training data, prioritize quality over quantity. Incorrect annotations will teach the model wrong patterns, degrading performance. If you're unsure about an annotation, it's better to leave it out than to include an incorrect one. For resolvers, only include toponyms where you're confident about the correct gazetteer linkage.

For recognizers, include diverse examples that cover different types of place names (countries, cities, landmarks, regions) and different contexts (various sentence structures, positions within sentences). For resolvers, include examples where disambiguation is challenging—toponyms with multiple plausible candidates where context is crucial.

If you have limited training data, consider using data augmentation techniques. For recognizers, you might create synthetic examples by substituting place names while preserving sentence structure. For resolvers, you might generate additional contexts for the same place names. However, be careful that augmented examples remain realistic and don't introduce artifacts.

Monitor your training process. If training loss decreases but validation performance plateaus or degrades, you're overfitting and should reduce the number of epochs, increase dropout, or gather more training data. If both training and validation performance are poor, your model might be underfitting—try training longer, using a larger model, or reducing regularization.

When training resolvers, the gazetteer you train with matters significantly. If your application focuses on a specific geographic region, using a regional gazetteer like SwissNames3D will generally give better results than using a global gazetteer like GeoNames, because the model can specialize in distinguishing between locations in that region rather than needing to handle the entire world.

Finally, document your training process thoroughly. Record the exact data used for training, the hyperparameters chosen, and the evaluation metrics achieved. This documentation is essential for reproducibility and for understanding how well the model might perform on different types of data.

Next Steps
----------

Now that you understand training, you can explore:

- :doc:`modules` - Learn more about the module architecture and creating custom modules
- :doc:`gazetteers` - Understand the geographic databases used for resolution
- :doc:`working_with_projects` - Use projects to organize training and evaluation workflows

For complete API documentation of training methods, see the :doc:`../api/project` and :doc:`../api/modules` references.

