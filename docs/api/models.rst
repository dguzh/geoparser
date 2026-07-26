Models
======

Document
--------

.. autoclass:: geoparser.db.models.Document
   :members:
   :show-inheritance:
   :exclude-members: id, project_id, project, references, recognitions, text, toponyms, model_config, model_post_init

   The Document model represents a text document that has been added to a project for geoparsing.

   **Properties:**

   .. py:attribute:: text
      :type: str
      :no-index:

      The full text content of the document.

   .. py:attribute:: toponyms
      :type: List[Reference]
      :no-index:

      Returns references (identified place names) filtered by the recognizer configured in the current context.
      This property is used to access the place names that were identified by a specific recognizer module.

Reference
---------

.. autoclass:: geoparser.db.models.Reference
   :members:
   :show-inheritance:
   :exclude-members: id, document_id, recognizer_id, document, recognizer, referents, resolutions, start, end, text, location, model_config, model_post_init

   The Reference model represents an identified place name (toponym) within a document.

   **Properties:**

   .. py:attribute:: start
      :type: int
      :no-index:

      The starting character position of the place name in the document text.

   .. py:attribute:: end
      :type: int
      :no-index:

      The ending character position of the place name in the document text.

   .. py:attribute:: text
      :type: Optional[str]
      :no-index:

      The actual text of the place name as it appears in the document. This is typically
      extracted automatically from the document text using the start and end positions.

   .. py:attribute:: location
      :type: Optional[Feature]
      :no-index:

      Returns the resolved geographic feature from the resolver configured in the current context.
      This property provides access to the geographic entity that this place name refers to,
      or None if the place name could not be resolved.

Feature
-------

.. autoclass:: geoparser.gazetteer.feature.Feature
   :members:
   :show-inheritance:
   :exclude-members: id, names, identifier, type, data, geometry, crs, gazetteer_name

   The Feature class represents a geographic entity from an installed gazetteer.

   **Properties:**

   .. py:attribute:: identifier
      :type: str
      :no-index:

      The feature's stable identifier within its gazetteer (for example the geonameid
      for GeoNames features).

   .. py:attribute:: source
      :type: str
      :no-index:

      The name of the gazetteer source the feature was built from
      (for example ``allCountries``, ``cities500``, or ``swissNAMES3D_PKT``).

   .. py:attribute:: data
      :type: Dict[str, Any]
      :no-index:

      Returns the feature's data as a dictionary. The available keys depend
      on which gazetteer (and source) the feature comes from. For GeoNames, common
      keys include name, latitude, longitude, country_name, feature_name, population,
      and administrative divisions. For SwissNames3D, keys include NAME, OBJEKTART,
      GEMEINDE_NAME, KANTON_NAME, and elevation. This property is cached for performance.

   .. py:attribute:: geometry
      :type: Optional[BaseGeometry]
      :no-index:

      Returns the geographic geometry (point, line, or polygon) associated with this feature
      as a Shapely geometry object, in the gazetteer's coordinate reference system
      (``crs``). This property is cached for performance.

   .. py:attribute:: names
      :type: List[str]
      :no-index:

      All searchable names of this feature. This property is cached for performance.

