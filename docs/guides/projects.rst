.. _projects:

Managing Projects
=================

A project is a workspace that remembers. Documents you add and results you produce are stored under a name, so you can return to them in a later session — and, more usefully, run several different pipelines over the same corpus and keep every result set side by side.

When to Use One
---------------

``Geoparser.parse()`` is the right tool for analysis you run in one sitting: text in, results out, nothing stored. Most work is like that, and the :doc:`../quickstart` covers it.

Reach for a project when one of these is true:

- **The corpus is large enough that reprocessing it is painful.** Parse once, then query the results as often as you like.
- **You want to compare configurations.** Two recognizers, three similarity thresholds, a different gazetteer — run them all over the same documents and keep each set of results separately, which is what makes the comparison meaningful.
- **You are working with annotations.** Training and evaluation both need human-annotated data stored alongside model output, so that the two can be compared.
- **The work spans sessions.** Results survive closing Python.

The cost is bookkeeping: you name things, and you keep track of which name holds what. Projects record what has been processed, by which module, with which configuration, and every result is filed under a **tag** identifying the pipeline that produced it. Tags are the part worth understanding properly, and they are covered below. Full signatures for every method are in the :doc:`../api/project` reference.

.. note::

   ``Geoparser`` is the interface we expect to remain stable. The database-backed project layer is likely to become one option among several rather than the foundation everything sits on, so where either would serve, prefer ``Geoparser``.

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

After creating a project, you can add documents to it using the ``create_documents()`` method. This method takes a list of text strings, one per document:

.. code-block:: python

   from geoparser import Project

   project = Project("news_analysis")

   # Add a single document
   project.create_documents(["The summit took place in Geneva."])

   # Add multiple documents
   texts = [
       "London hosted the Olympic Games in 2012.",
       "The conference was held in Barcelona.",
       "Researchers gathered in Vienna to discuss the findings."
   ]
   project.create_documents(texts)

You can add more documents to the same project at any time, and they will accumulate in the project's collection.

Each document is stored under a unique identifier, and ``create_documents()`` returns those identifiers in the order the texts were given. If the texts come from an existing collection of yours — a database of articles, a set of files, or anything else — store the returned IDs with those records so that parsed results can later be matched to the originals:

.. code-block:: python

   articles = load_articles()  # your own records, whatever shape they have

   document_ids = project.create_documents([article["body"] for article in articles])

   for article, document_id in zip(articles, document_ids):
       article["document_id"] = document_id

Passing those IDs to ``get_documents()`` retrieves exactly those documents, in the order you asked for them:

.. code-block:: python

   # Results for one specific article
   documents = project.get_documents(ids=articles[0]["document_id"])

   # Or for a subset of your material, in your own order
   recent = [article["document_id"] for article in articles if article["year"] >= 2020]
   documents = project.get_documents(ids=recent)

This makes it possible to work with parts of a corpus separately, for instance to compare how a pipeline performs on older versus newer material, without reprocessing anything.

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

   # Or only specific ones, using the IDs from create_documents()
   documents = project.get_documents(ids=document_ids)

   # Access the results
   for doc in documents:
       print(f"Document: {doc.text}")
       for toponym in doc.toponyms:
           print(f"  - {toponym.text}", end="")
           location = toponym.location
           if location:
               data = location.data
               print(f" → {data.get('name')} ({data.get('latitude')}, {data.get('longitude')})")
           else:
               print(" (unresolved)")
       print()

The ``toponyms`` property on each document returns only the references that were identified by the recognizer associated with the current tag. Similarly, each reference's ``location`` property returns the feature resolved by the resolver associated with that tag. By default, when you don't specify a tag, the system uses the ``"latest"`` tag, which references the most recently run recognizer and resolver that were executed with this ``"latest"`` tag. If you run modules with a different tag, the ``"latest"`` tag remains unchanged and continues to reference the modules that were last run with ``"latest"``. This context-based filtering, controlled through tags, is explained in the next section.

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

Tags enable you to run multiple recognition and resolution strategies on the same corpus and compare their performance. Each tag maintains its own pointer to which recognizer and resolver were used, so when you call ``get_documents(tag="baseline")``, you see only the results from the modules associated with that tag. It's important to understand that tags are designed to represent complete processing pipelines, not individual modules. When using tags, always run both a recognizer and a resolver with the same tag, as resolution results are inherently tied to recognition results. Using different tags for recognition and resolution within the same pipeline will lead to invalid or incomplete results.

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

Projects support managing manually annotated data, which is essential for training custom models and evaluating system performance. You can create annotations programmatically using the ``create_references()`` and ``create_referents()`` methods:

.. code-block:: python

   from geoparser import Project

   project = Project("manual_annotations")

   texts = ["Paris is the capital of France."]
   project.create_documents(texts)

   # Create references (identified place names)
   references = [[(0, 5), (24, 30)]]  # "Paris" and "France"
   project.create_references(texts, references, tag="manual")

   # Create referents (resolved locations)
   referents = [[("geonames", "2988507"), ("geonames", "3017382")]]
   project.create_referents(texts, references, referents, tag="manual")

Positions are character offsets into the document text, with ``end`` exclusive — exactly what ``text[start:end]`` expects. Check them before annotating in bulk: ``"Paris is the capital of France."[24:30]`` is ``'France'``, whereas ``[23:29]`` would give ``' Franc'``. Reference text is recomputed from the offsets rather than taken from any text you supply, so an off-by-one is stored silently.

These methods store the annotations in the database using internal recognizer and resolver modules. The annotations can then be used for training or evaluation purposes.

Alternatively, you can load annotations from JSON files exported from annotation tools:

.. code-block:: python

   from geoparser import Project

   project = Project("annotated_corpus")

   # Load annotations from a JSON file
   # Set create_documents=True if documents aren't already in the project
   project.load_annotations(
       path="annotations.json",
       tag="annotator",
       create_documents=True
   )

   # Access the manually annotated toponyms
   documents = project.get_documents(tag="annotator")
   for doc in documents:
       print(f"Document: {doc.text}")
       print(f"  Annotated toponyms: {len(doc.toponyms)}")

The JSON file should follow this structure:

.. code-block:: json

   {
       "gazetteer": "geonames",
       "documents": [
           {
               "text": "Paris is the capital of France.",
               "toponyms": [
                   {
                       "start": 0,
                       "end": 5,
                       "text": "Paris",
                       "loc_id": "2988507"
                   },
                   {
                       "start": 24,
                       "end": 30,
                       "text": "France",
                       "loc_id": "3017382"
                   }
               ]
           }
       ]
   }

The ``loc_id`` field should contain the identifier from the specified gazetteer, or empty string/null for toponyms that were not linked to locations. Only ``start`` and ``end`` are read for each toponym; the ``"text"`` field is documentation for the reader, and the stored reference text is recomputed from the offsets.

This is the format the :doc:`annotator <annotating>` exports, so annotations made there can be loaded without conversion.

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
