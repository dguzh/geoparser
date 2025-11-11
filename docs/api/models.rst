Models
======

Document
--------

.. autoclass:: geoparser.db.models.Document
   :members: text, toponyms
   :show-inheritance:
   :exclude-members: id, project_id, project, references, recognitions, model_config, model_post_init

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
   :members: start, end, text, location
   :show-inheritance:
   :exclude-members: id, document_id, recognizer_id, document, recognizer, referents, resolutions, model_config, model_post_init

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

.. autoclass:: geoparser.db.models.Feature
   :members: location_id_value, data, geometry
   :show-inheritance:
   :exclude-members: id, source_id, source, names, model_config, model_post_init

   The Feature model represents a geographic entity from a gazetteer.

   **Properties:**

   .. py:attribute:: location_id_value
      :type: str
      :no-index:

      The identifier value for this feature within its gazetteer. For GeoNames, this is the
      geonameid; for SwissNames3D, it's the UUID. This value can be used to uniquely
      identify and retrieve the feature.

   .. py:attribute:: data
      :type: Optional[Dict[str, Any]]
      :no-index:

      Returns the complete gazetteer row data for this feature as a dictionary. The available
      attributes depend on which gazetteer the feature comes from. For GeoNames, common
      attributes include name, latitude, longitude, country_name, feature_name, population,
      and administrative divisions. For SwissNames3D, attributes include NAME, OBJEKTART,
      GEMEINDE_NAME, KANTON_NAME, and elevation. This property is cached for performance.

   .. py:attribute:: geometry
      :type: Optional[BaseGeometry]
      :no-index:

      Returns the geographic geometry (point, line, or polygon) associated with this feature
      as a Shapely geometry object. This property is cached for performance.

