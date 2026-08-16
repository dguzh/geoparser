Models
======

The objects a pipeline returns. You never construct these yourself — they come back from
:meth:`Geoparser.parse() <geoparser.geoparser.geoparser.Geoparser.parse>` and
:meth:`Project.get_documents() <geoparser.project.project.Project.get_documents>` — so only
the attributes you read are documented here.

Document
--------

.. py:class:: Document
   :module: geoparser.db.models.document

   One text that was parsed.

   .. py:attribute:: text
      :type: str

      The full text content of the document, as stored. Line endings are normalized to
      ``\n`` when the document is created, which matters when matching annotations against
      it by text.

   .. py:attribute:: id
      :type: uuid.UUID

      The document's unique identifier. These are the values returned by
      :meth:`Project.create_documents() <geoparser.project.project.Project.create_documents>`
      and accepted by the ``ids`` argument of
      :meth:`Project.get_documents() <geoparser.project.project.Project.get_documents>`.
      Store them alongside your own records to relate results back to where the text came from.

   .. py:attribute:: toponyms
      :type: List[Reference]

      The place names found in this document: the references produced by the recognizer
      registered for the current tag.

      Because it is filtered by tag, this is empty when no recognizer has been run under the
      tag you retrieved the document with — which is a different situation from a recognizer
      that ran and found nothing, though they look the same. See :doc:`../guides/projects`.

Reference
---------

.. py:class:: Reference
   :module: geoparser.db.models.reference

   One recognized place name within a document — a *toponym*. Obtained from
   :attr:`Document.toponyms <geoparser.db.models.document.Document.toponyms>`.

   .. py:attribute:: text
      :type: Optional[str]

      The place name as it appears in the document. Derived from the document text using
      ``start`` and ``end`` rather than stored independently, so it always reflects the offsets.

   .. py:attribute:: start
      :type: int

      Character offset in the document text where the place name begins.

   .. py:attribute:: end
      :type: int

      Character offset where the place name ends, exclusive — so
      ``document.text[reference.start:reference.end]`` is the place name. Widen the slice to
      recover the surrounding context.

   .. py:attribute:: location
      :type: Optional[Feature]

      The gazetteer feature this place name was resolved to by the resolver registered for
      the current tag, or ``None`` if it was not resolved.

      ``None`` is a normal outcome: the place may be absent from the gazetteer, or no
      candidate may have passed the resolver's confidence threshold. Always check before
      reading attributes.

Feature
-------

.. py:class:: Feature
   :module: geoparser.gazetteer.feature

   One place in a gazetteer. Returned by
   :attr:`Reference.location <geoparser.db.models.reference.Reference.location>`, and by
   :meth:`Gazetteer.search() <geoparser.gazetteer.gazetteer.Gazetteer.search>` and
   :meth:`Gazetteer.find() <geoparser.gazetteer.gazetteer.Gazetteer.find>`.

   Two features are equal when they have the same identifier in the same gazetteer, so they
   can be used as dictionary keys or set members to aggregate mentions by place.

   .. py:attribute:: identifier
      :type: str

      The feature's stable identifier within its gazetteer — the geonameid for GeoNames, a
      UUID for SwissNames3D, whatever a custom gazetteer defines. This is what to store when
      recording a resolution, and what to group by when counting mentions per place: names
      are ambiguous, identifiers are not.

   .. py:attribute:: data
      :type: Dict[str, Any]

      The feature's attributes.

      Which keys exist depends on the gazetteer, and on the source within it, so read them
      with ``.get()`` rather than by subscripting. For GeoNames, common keys are ``name``,
      ``latitude``, ``longitude``, ``country_name``, ``feature_name``, ``feature_class``, and
      ``population``; for SwissNames3D, ``NAME``, ``OBJEKTART``, ``KANTON_NAME``, and
      ``HOEHE``. Full lists are in :doc:`../guides/gazetteers`. Cached after first access.

   .. py:attribute:: geometry
      :type: Optional[shapely.geometry.base.BaseGeometry]

      The feature's geometry as a Shapely object, in the coordinate reference system given by
      ``crs`` — usually a point, but lines, polygons, and multi-part geometries occur.

      ``None`` when the gazetteer records the place by name without locating it — roughly a
      sixth of Pleiades places, for instance, are attested in texts but never located.
      Cached after first access.

   .. py:attribute:: crs
      :type: str

      The coordinate reference system ``geometry`` is expressed in, as an authority code such
      as ``EPSG:4326``. Fixed per gazetteer and chosen when it is built, so every feature from
      one gazetteer shares it. Use this rather than assuming, when exporting spatial data from
      a custom gazetteer.

   .. py:attribute:: names
      :type: List[str]

      Every name the feature is searchable by: its main name plus any historical spellings,
      transliterations, translations, and abbreviations the gazetteer records. Unordered and
      unlabelled — there is no notion of a preferred name or of a name's language.
      Cached after first access.

   .. py:attribute:: source
      :type: str

      The gazetteer source this feature was built from, such as ``allCountries`` for GeoNames.
      Useful for telling apart features of different kinds within one gazetteer, since
      attributes vary by source.
