.. This is the one copy of the transformer prerequisite caveat. Every page that shows
   ``en_core_web_trf`` pulls it in with
   ``.. include:: /_snippets/spacy-transformer-requirements.rst``, so the three facts
   below are stated identically wherever the model appears. ``tests/unit/test_docs.py``
   fails if a page presents the model without the include.

.. note::

   ``en_core_web_trf`` is a transformer pipeline, and its first component comes from
   ``spacy-curated-transformers`` — a plugin that spaCy does not install with itself.
   Without the plugin the model cannot be loaded at all, and spaCy reports
   ``Can't find factory for 'curated_transformer'``. Install it alongside Geoparser:

   .. code-block:: bash

      pip install spacy-curated-transformers

   The plugin publishes no release for Python 3.14. On that version, use
   ``en_core_web_lg`` instead: it is the largest spaCy pipeline that needs no plugin, it
   is more accurate than the default ``en_core_web_sm``, and Geoparser downloads it on
   first use like any other spaCy model.
