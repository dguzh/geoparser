Models
======

Document
--------

.. autoclass:: geoparser.db.models.Document
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: id, project_id, project, references, recognitions

   The Document model represents a text document that has been added to a project for geoparsing.

   **Key Properties:**

   .. py:attribute:: text
      :type: str

      The full text content of the document.

   .. py:attribute:: toponyms
      :type: List[Reference]

      Returns references (identified place names) filtered by the recognizer configured in the current context.
      This property is used to access the place names that were identified by a specific recognizer module.

Reference
---------

.. autoclass:: geoparser.db.models.Reference
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: id, document_id, recognizer_id, document, recognizer, referents, resolutions

   The Reference model represents an identified place name (toponym) within a document.

   **Key Properties:**

   .. py:attribute:: start
      :type: int

      The starting character position of the place name in the document text.

   .. py:attribute:: end
      :type: int

      The ending character position of the place name in the document text.

   .. py:attribute:: text
      :type: Optional[str]

      The actual text of the place name as it appears in the document. This is typically
      extracted automatically from the document text using the start and end positions.

   .. py:attribute:: location
      :type: Optional[Feature]

      Returns the resolved geographic feature from the resolver configured in the current context.
      This property provides access to the geographic entity that this place name refers to,
      or None if the place name could not be resolved.

Feature
-------

.. autoclass:: geoparser.db.models.Feature
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: id, source_id, source, names

   The Feature model represents a geographic entity from a gazetteer.

   **Key Properties:**

   .. py:attribute:: location_id_value
      :type: str

      The identifier value for this feature within its gazetteer. For GeoNames, this is the
      geonameid; for SwissNames3D, it's the UUID. This value can be used to uniquely
      identify and retrieve the feature.

   .. py:attribute:: data
      :type: Optional[Dict[str, Any]]

      Returns the complete gazetteer row data for this feature as a dictionary. The available
      attributes depend on which gazetteer the feature comes from. For GeoNames, common
      attributes include name, latitude, longitude, country_name, feature_name, population,
      and administrative divisions. For SwissNames3D, attributes include NAME, OBJEKTART,
      GEMEINDE_NAME, KANTON_NAME, and elevation. This property is cached for performance.

   .. py:attribute:: geometry
      :type: Optional[BaseGeometry]

      Returns the geographic geometry (point, line, or polygon) associated with this feature
      as a Shapely geometry object. This property is cached for performance.

Context Filtering
-----------------

The Document and Reference models use a context-based filtering mechanism to determine which
results to display. When you call ``project.get_documents(tag="mytag")``, the project retrieves
the recognizer and resolver IDs associated with that tag and sets them as the viewing context
on the returned documents and their references.

This context filtering allows you to work with results from specific processing modules without
explicitly tracking module IDs yourself. When you access ``doc.toponyms``, you get only the
references identified by the recognizer associated with the current context. When you access
``ref.location``, you get the feature resolved by the resolver associated with the current context.

If no context is set (recognizer_id or resolver_id is None), the corresponding properties return
empty results. This ensures that you only see results from modules you've explicitly chosen to view.

