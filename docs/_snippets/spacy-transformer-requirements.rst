.. This is the one copy of the transformer prerequisite caveat. Every page that shows
   ``en_core_web_trf`` pulls it in with
   ``.. include:: /_snippets/spacy-transformer-requirements.rst``, so the facts below are
   stated identically wherever the model appears. ``tests/unit/test_docs.py`` fails if a
   page presents the model without the include, if a notebook or build file presents it
   without the pinned requirement, or if any source installs the plugin unpinned.

.. note::

   ``en_core_web_trf`` is a transformer pipeline, and its first component comes from
   ``spacy-curated-transformers`` — a plugin that spaCy does not install with itself.
   Without the plugin the model cannot be loaded at all, and spaCy reports
   ``[E002] Can't find factory for 'curated_transformer'``. Install it alongside
   Geoparser, with the bound the model itself declares:

   .. code-block:: bash

      pip install "spacy-curated-transformers>=0.2.2,<1.0.0"

   The bound is not optional. Unpinned, pip installs the plugin's 2.x line, which is
   built for a later spaCy generation and asks for a ``thinc`` release that Geoparser's
   spaCy 3.8 cannot use. On Python 3.14 the bound resolves to 0.3.0 rather than 0.3.1,
   which declares ``Requires-Python <3.14``.

   If you would rather not take on the plugin and the PyTorch install behind it,
   ``en_core_web_lg`` needs neither: it is the largest English spaCy pipeline that
   requires no plugin, and Geoparser downloads it on first use like any other spaCy
   model.
