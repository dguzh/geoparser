.. _annotating:

Annotating Data
===============

Two things require annotated data: training a module on your own material, and measuring how well a pipeline performs. Both need the same thing — texts where a human has marked which words are place names and which places they refer to.

The library ships a web application for producing exactly that. This guide covers what it does, how to run it, and how its output feeds back into a project.

.. note::

   The annotator is a standalone tool rather than an integrated part of the library. It was built for an earlier architecture and was adapted to keep annotation working through the redesign, so it has its own database and does not share projects with the rest of the library. Annotations move between the two as a JSON file, which is the part to depend on: the application itself is likely to be reworked or replaced.

Do You Need It?
---------------

You do not need annotations to geoparse text. The built-in modules are pre-trained and work out of the box.

You do need them if you want to:

- **Fine-tune a module** for a language, period, or domain the defaults handle poorly — see :doc:`training`
- **Measure performance** on your own material, rather than trusting figures from someone else's corpus
- **Build a gold-standard corpus** as a research output in its own right

If you already have annotations in another format, you do not need the application either: ``create_references()`` and ``create_referents()`` take spans and identifiers directly, as shown in :doc:`projects`. The annotator is for producing them by hand.

Starting the Application
------------------------

.. code-block:: bash

   python -m geoparser annotator

It starts a local web server and opens ``http://127.0.0.1:5000/`` in your browser. Stop it with :kbd:`Ctrl-C`.

.. warning::

   The server listens on all network interfaces and has no authentication, so anyone who can reach your machine on port 5000 can read and edit your annotations. Use it on a trusted network only.

The annotator offers **GeoNames** and **SwissNames3D**, whichever of them you have installed. Install one first if you have not already — see :doc:`../installation`.

The Workflow
------------

**1. Start a session.** A session is one annotation job: a set of documents, a chosen gazetteer, and the annotations made so far. Upload one or more plain text files and pick the gazetteer to link places to. The gazetteer is fixed for the session, because identifiers only mean something relative to it.

**2. Pre-annotate, or don't.** For each document you can run the recognizer to propose candidate spans, then correct them, which is considerably faster than marking every name by hand. Or annotate from scratch if you would rather not be anchored by the model's suggestions — for building an unbiased evaluation set, that is the better choice.

**3. Mark the place names.** Select a span of text to record it as a toponym. Spans may not overlap; attempting it is refused with ``Overlap with existing toponym.`` rather than silently accepted, since overlapping annotations have no consistent interpretation downstream.

**4. Link each name to a place.** For a marked toponym, the annotator searches the gazetteer and shows the candidates with their attributes and coordinates so you can tell one Springfield from another. Choose the right one. A toponym you cannot resolve — a fictional place, or one genuinely absent from the gazetteer — can be left unlinked, and that is meaningful information rather than an omission: it records that a human could not resolve it either.

**5. Download the annotations.** The session exports as a JSON file. Sessions are also stored in the annotator's own database, so you can close the browser and continue later.

Two session settings are worth knowing. *Auto-close annotation modal* moves you straight on after each choice, which is faster once you are used to the interface. *One sense per discourse* applies your choice to other occurrences of the same name in the same document, on the assumption that a repeated name in one text usually means the same place — often true, occasionally not, so review the result.

The Annotation Format
---------------------

The export looks like this:

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

``start`` and ``end`` are character offsets into ``text``, with ``end`` exclusive. ``loc_id`` is the identifier in the named gazetteer, or an empty string or ``null`` for a toponym that was not linked.

Because the format is plain JSON, you can also generate it from an existing annotated corpus and skip the application entirely. Two things to get right if you do: only ``start`` and ``end`` are read for each toponym — the ``"text"`` field is for human readers, and the stored text is recomputed from the offsets — and the document ``text`` must match exactly what is in your project, since annotations are matched to documents by text equality.

Loading Annotations into a Project
----------------------------------

Bring the exported file into a project with ``load_annotations()``:

.. code-block:: python

   from geoparser import Project

   project = Project("annotated_corpus")

   project.load_annotations(
       path="annotations_5f3a.json",
       tag="gold",
       create_documents=True,
   )

   for document in project.get_documents(tag="gold"):
       print(f"{len(document.toponyms)} annotated toponyms")

Two arguments decide how it behaves.

``create_documents=True`` adds the annotated texts to the project as documents. Use it when the project is empty. Leave it ``False`` when the documents are already there — from ``create_documents()`` earlier, say — and the annotations should attach to those. In that case the texts must match exactly, or the annotation is skipped with no error.

``tag`` is the name this annotation set gets within the project. It is how you refer to the annotations afterwards, and it must be the same tag you later train or evaluate against — a mismatch is the most common reason training reports finding no examples. Human annotations and model output should always carry different tags, so that ``get_documents(tag="gold")`` and ``get_documents(tag="predicted")`` can be compared.

.. code-block:: python

   # Human annotations
   project.load_annotations(path="gold.json", tag="gold", create_documents=True)

   # Model output over the same documents
   project.run_recognizer(SpacyRecognizer(), tag="predicted")
   project.run_resolver(SentenceTransformerResolver(), tag="predicted")

   gold = project.get_documents(tag="gold")
   predicted = project.get_documents(tag="predicted")

From here the annotations are ordinary project data: they can train a module, as in :doc:`training`, or serve as the reference set for evaluation.

Practical Advice
----------------

Annotation is slower than people expect — budget on the order of an hour per few thousand words for careful work, more if the material is unfamiliar or the places are obscure.

**Write down your decisions as you go.** Do metonymic uses count, where "Washington" means a government rather than a city? Do you annotate nested names like "Cambridge, Massachusetts" as one toponym or two? Are demonyms such as "Swiss" in scope? None of these has a single right answer, but inconsistency across a corpus is worse than any of the possible answers, and you will not remember on day three what you decided on day one.

**Annotate a held-out set separately.** Data used for training cannot also measure performance. Split the material first, so the temptation does not arise.

**Have a second person annotate a sample.** Agreement between two annotators on the same few documents tells you how reliable your guidelines are, and is worth reporting in any publication that rests on the corpus.

**Keep the JSON exports.** They are the durable artefact — small, plain text, and readable without this library. The annotator's own database is a working file, not an archive.

Next Steps
----------

- :doc:`training` — fine-tune a recognizer or resolver on these annotations
- :doc:`projects` — organize annotated and predicted results side by side
