.. _working_with_projects:

Working with Projects
=====================

While the simple ``Geoparser.parse()`` interface is convenient for quick tasks, projects provide a more powerful approach for research and production workflows. Projects are persistent workspaces that store documents and processing results in a local database, enabling you to compare different processing strategies, manage annotations, and build reproducible analysis pipelines.

Creating and Loading Projects
------------------------------

Projects are identified by name. When you create a ``Project`` instance, it either creates a new project in the database or loads an existing one with that name:

.. code-block:: python

   from geoparser import Project

   # Create a new project or load an existing one
   project = Project("research_corpus")

Once created, a project persists in the database until explicitly deleted. You can close your Python session, come back later, and reload the same project by using the same name.

Adding Documents
----------------

After creating a project, you can add documents to it using the ``create_documents()`` method. This method accepts either a single text string or a list of text strings:

.. code-block:: python

   from geoparser import Project

   project = Project("news_analysis")

   # Add a single document
   project.create_documents("The summit took place in Geneva.")

   # Add multiple documents
   texts = [
       "London hosted the Olympic Games in 2012.",
       "The conference was held in Barcelona.",
       "Researchers gathered in Vienna to discuss the findings."
   ]
   project.create_documents(texts)

Documents added to a project are stored in the database with unique identifiers. You can add more documents to the same project at any time, and they will accumulate in the project's collection.

Running Processing Modules
---------------------------

Once you have documents in a project, you can run recognition and resolution modules to identify and resolve place names. The project manages the execution and stores the results:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   project = Project("news_analysis")

   # Create module instances
   recognizer = SpacyRecognizer()
   resolver = SentenceTransformerResolver()

   # Run the recognizer to identify place names
   project.run_recognizer(recognizer)

   # Run the resolver to link place names to locations
   project.run_resolver(resolver)

The ``run_recognizer()`` method processes all documents in the project that haven't been processed by this specific recognizer yet. Similarly, ``run_resolver()`` processes all references that haven't been resolved by this specific resolver. This means you can safely call these methods multiple times—only unprocessed items will be handled.

Retrieving Results
------------------

After running modules on your project, you can retrieve the processed documents using the ``get_documents()`` method:

.. code-block:: python

   from geoparser import Project

   project = Project("news_analysis")

   # Get all documents with their results
   documents = project.get_documents()

   # Access the results
   for doc in documents:
       print(f"Document: {doc.text}")
       for toponym in doc.toponyms:
           print(f"  - {toponym.text}", end="")
           if toponym.location:
               print(f" → {toponym.location.data.get('name')}")
           else:
               print(" (unresolved)")
       print()

The ``toponyms`` property on each document returns only the references that were identified by the recognizer you're currently viewing. Similarly, each reference's ``location`` property returns the feature resolved by the resolver you're viewing. This context-based filtering is controlled through tags, as explained in the next section.

Understanding Tags
------------------

Tags provide a way to manage multiple result sets within the same project. When you run a recognizer or resolver, you can optionally specify a tag to associate with those results. The default tag is ``"latest"``.

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   project = Project("comparison_study")

   # Add documents
   project.create_documents([
       "Scientists met in Copenhagen to discuss climate change.",
       "The treaty was signed in Kyoto."
   ])

   # Run with default spaCy model and tag as "baseline"
   recognizer_baseline = SpacyRecognizer(model_name="en_core_web_sm")
   resolver_baseline = SentenceTransformerResolver()
   
   project.run_recognizer(recognizer_baseline, tag="baseline")
   project.run_resolver(resolver_baseline, tag="baseline")

   # Run with transformer-based model and tag as "transformer"
   recognizer_trf = SpacyRecognizer(model_name="en_core_web_trf")
   resolver_trf = SentenceTransformerResolver(
       model_name="dguzh/geo-all-distilroberta-v1"
   )
   
   project.run_recognizer(recognizer_trf, tag="transformer")
   project.run_resolver(resolver_trf, tag="transformer")

   # Compare results from different configurations
   baseline_docs = project.get_documents(tag="baseline")
   transformer_docs = project.get_documents(tag="transformer")

   print("Baseline Results:")
   for doc in baseline_docs:
       print(f"  Found {len(doc.toponyms)} toponyms")

   print("\nTransformer Results:")
   for doc in transformer_docs:
       print(f"  Found {len(doc.toponyms)} toponyms")

Tags enable you to run multiple recognition and resolution strategies on the same corpus and compare their performance. Each tag maintains its own pointer to which recognizer and resolver were used, so when you call ``get_documents(tag="baseline")``, you see only the results from the modules associated with that tag.

Comparative Workflows
---------------------

Projects are particularly useful for comparing different processing configurations. You can systematically evaluate how different recognizers, resolvers, or parameters affect the geoparsing results:

.. code-block:: python

   from geoparser import Project
   from geoparser.modules import SpacyRecognizer, SentenceTransformerResolver

   project = Project("parameter_study")
   project.create_documents([
       "The delegation traveled from Brussels to Amsterdam.",
       "Trade routes connected Venice, Constantinople, and Alexandria."
   ])

   # Test different similarity thresholds
   recognizer = SpacyRecognizer()
   
   for threshold in [0.5, 0.6, 0.7, 0.8]:
       resolver = SentenceTransformerResolver(min_similarity=threshold)
       tag = f"threshold_{threshold}"
       
       project.run_recognizer(recognizer, tag=tag)
       project.run_resolver(resolver, tag=tag)
       
       docs = project.get_documents(tag=tag)
       resolved_count = sum(
           1 for doc in docs 
           for toponym in doc.toponyms 
           if toponym.location is not None
       )
       print(f"Threshold {threshold}: {resolved_count} resolved toponyms")

This approach enables reproducible experiments where you can precisely control and document which processing configuration produced which results.

Working with Annotations
------------------------

Projects support loading manually annotated data, which is essential for training custom models and evaluating system performance. You can load annotations from JSON files that follow the annotator format:

.. code-block:: python

   from geoparser import Project

   project = Project("annotated_corpus")

   # Load annotations from a JSON file
   # Set create_documents=True if documents aren't already in the project
   project.load_annotations(
       path="annotations.json",
       tag="manual",
       create_documents=True
   )

   # Access the manually annotated toponyms
   documents = project.get_documents(tag="manual")
   for doc in documents:
       print(f"Document: {doc.text}")
       print(f"  Annotated toponyms: {len(doc.toponyms)}")

The JSON file should contain a ``gazetteer`` field specifying which gazetteer was used, a ``documents`` array with document texts, and for each document a ``toponyms`` array with ``start``, ``end``, ``text``, and ``loc_id`` fields. The ``loc_id`` should be the identifier from the specified gazetteer, or empty string/null for toponyms that were not linked to locations.

You can also create annotations programmatically using the ``create_references()`` and ``create_referents()`` methods:

.. code-block:: python

   from geoparser import Project

   project = Project("manual_annotations")

   texts = ["Paris is the capital of France."]
   project.create_documents(texts)

   # Create references (identified place names)
   references = [[(0, 5), (23, 29)]]  # "Paris" and "France"
   project.create_references(texts, references, tag="manual")

   # Create referents (resolved locations)
   referents = [[("geonames", "2988507"), ("geonames", "3017382")]]
   project.create_referents(texts, references, referents, tag="manual")

These methods use internal recognizer and resolver modules (``ManualRecognizer`` and ``ManualResolver``) to store the annotations in the database. The annotations can then be used for training or evaluation purposes.

Deleting Projects
-----------------

When you're done with a project and want to free up database space, you can delete it using the ``delete()`` method:

.. code-block:: python

   from geoparser import Project

   project = Project("temporary_analysis")
   # ... work with the project ...
   
   # Delete the project and all associated data
   project.delete()

This removes the project and all its documents, references, and referents from the database. The deletion is permanent and cannot be undone, so use this method carefully.

Best Practices
--------------

When working with projects, consider these practices to maintain organized and reproducible workflows. Choose meaningful project names that reflect the corpus or research question. Use descriptive tags that indicate the processing configuration, such as ``"spacy_sm_geonames"`` or ``"annotator_john"``. Document your processing pipeline in code or notebooks so you can recreate results later.

For large corpora, add documents in batches rather than one at a time to improve database performance. If you're running multiple experiments, consider creating separate projects for each major variant rather than managing many tags within a single project. When comparing results, retrieve documents with different tags separately and analyze them side by side.

For training and evaluation workflows, keep your annotated data in a dedicated project separate from experimental runs. This ensures that gold-standard annotations remain unchanged while you iterate on different processing approaches.

Next Steps
----------

Now that you understand project-based workflows, you can explore:

- :doc:`modules` - Learn about the different recognizers and resolvers available
- :doc:`training` - Use project annotations to train custom models
- :doc:`gazetteers` - Understand how geographic databases work

For complete API documentation of the Project class, see the :doc:`../api/project` reference.

