.. _modules:

Modules
=======

This guide explains how to use the built-in recognizer and resolver modules, customize their behavior, and create your own custom modules.

Overview
--------

The Irchel Geoparser uses a modular architecture where recognition and resolution are handled by pluggable components called modules. This design allows you to mix and match different processing strategies, create custom implementations, and extend the system without modifying its core.

Modules come in two types: recognizers identify place names in text, while resolvers link these place names to geographic entities in gazetteers. Each module type implements a specific interface that defines how it interacts with the rest of the system. The key aspect of this architecture is that modules are completely database-agnostic—they operate purely on text and return predictions, while service layers handle all database interactions.

When you run a module on a project, the system stores both the module's results and its configuration in the database. This enables the system to track which results came from which module, avoid reprocessing data unnecessarily, and support comparative analysis of different module configurations. Each module is uniquely identified by hashing its name and configuration parameters, ensuring that modules with different settings are treated as distinct processing approaches.

Built-in Recognizers
--------------------

SpacyRecognizer
~~~~~~~~~~~~~~~

The ``SpacyRecognizer`` uses spaCy's named entity recognition capabilities to identify potential place names in text. By default, it recognizes entities labeled as geopolitical entities (GPE), locations (LOC), and facilities (FAC) as potential toponyms, though this can be customized.

To use the SpacyRecognizer with default settings:

.. code-block:: python

   from geoparser.modules import SpacyRecognizer

   recognizer = SpacyRecognizer()

The default configuration uses the ``en_core_web_sm`` model and recognizes entities of types FAC, GPE, and LOC. You can customize both of these parameters:

.. code-block:: python

   from geoparser.modules import SpacyRecognizer

   # Use a more accurate transformer-based model
   recognizer = SpacyRecognizer(
       model_name="en_core_web_trf",
       entity_types=["GPE", "LOC"]  # Only geopolitical entities and locations
   )

The ``model_name`` parameter accepts any spaCy model that includes a named entity recognizer. Larger models like ``en_core_web_trf`` provide higher accuracy but require more memory and processing time. For non-English texts, specify an appropriate spaCy model for that language.

The ``entity_types`` parameter allows you to filter which entity types are considered as toponyms. By default, the recognizer includes FAC (facilities like buildings and landmarks), GPE (geopolitical entities like countries and cities), and LOC (natural locations and regions). If your application only needs to identify country and city names, you might restrict this to just GPE.

Built-in Resolvers
------------------

SentenceTransformerResolver
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``SentenceTransformerResolver`` uses transformer-based language models to disambiguate place names by comparing contextual embeddings. It extracts the context surrounding each place name, retrieves candidate locations from the gazetteer, generates textual descriptions of these candidates, and selects the candidate whose description most closely matches the context based on embedding cosine similarity.

To use the SentenceTransformerResolver with default settings:

.. code-block:: python

   from geoparser.modules import SentenceTransformerResolver

   resolver = SentenceTransformerResolver()

The default configuration uses the ``dguzh/geo-all-MiniLM-L6-v2`` model with the ``geonames`` gazetteer, a minimum similarity threshold of 0.7, and up to 3 iterations through increasingly broad search methods. You can customize any of these parameters:

.. code-block:: python

   from geoparser.modules import SentenceTransformerResolver

   # Use a more accurate model with Swiss gazetteer
   resolver = SentenceTransformerResolver(
       model_name="dguzh/geo-all-distilroberta-v1",
       gazetteer_name="swissnames3d",
       min_similarity=0.6,  # Accept more candidates
       max_iter=2  # Less exhaustive candidate search
   )

The ``model_name`` parameter specifies which SentenceTransformer model to use for generating embeddings. The library provides two pre-trained models fine-tuned for toponym disambiguation: ``dguzh/geo-all-MiniLM-L6-v2`` offers fast processing with good accuracy, while ``dguzh/geo-all-distilroberta-v1`` provides higher accuracy at the cost of speed and memory. These models were trained on English news articles and work best with English text and the GeoNames gazetteer. For other languages or domains, you should train a custom model as described in the :doc:`training` guide.

The ``gazetteer_name`` parameter determines which geographic database to search. The specified gazetteer must be installed on your system. Each gazetteer has different coverage and attribute schemas, so make sure your application requirements match the gazetteer's capabilities.

The ``min_similarity`` threshold controls how confident the resolver must be before accepting a match. Higher thresholds reduce false positives but may leave more toponyms unresolved. Lower thresholds resolve more toponyms but may introduce incorrect matches.

The ``max_iter`` parameter controls how aggressively the resolver searches for candidates. The resolver uses an iterative strategy starting with exact string matching and progressively relaxing to phrase matching, partial matching, and fuzzy matching. Each iteration also considers more rank tiers of search results. A higher ``max_iter`` value means the resolver will try harder to find candidates for difficult toponyms, but this increases processing time.

For gazetteers other than GeoNames and SwissNames3D, you need to provide a custom ``attribute_map`` that tells the resolver which attributes to use when generating location descriptions:

.. code-block:: python

   from geoparser.modules import SentenceTransformerResolver

   # Custom gazetteer with different attribute names
   custom_map = {
       "name": "place_name",
       "type": "category",
       "level1": "country",
       "level2": "region",
       "level3": "district"
   }

   resolver = SentenceTransformerResolver(
       gazetteer_name="custom_gazetteer",
       attribute_map=custom_map
   )

The attribute map should specify which columns in your gazetteer correspond to the name, type, and hierarchical administrative levels. The resolver uses these attributes to generate textual descriptions like "Paris (city) in Île-de-France, France".

The SentenceTransformerResolver works best when place names have distinctive contexts that help disambiguate them. For example, "I visited the Eiffel Tower in Paris" provides strong contextual clues. Short texts with minimal context or lists of place names without surrounding text present more challenging scenarios where the resolver may struggle.

Creating Custom Recognizers
----------------------------

You can create custom recognizers by implementing the ``Recognizer`` interface. A recognizer is a class that inherits from ``Recognizer`` and implements a ``predict()`` method that takes a list of texts and returns predictions for each text.

The basic structure of a custom recognizer looks like this:

.. code-block:: python

   import typing as t
   from geoparser.modules.recognizers import Recognizer

   class MyCustomRecognizer(Recognizer):
       NAME = "MyCustomRecognizer"
       
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Initialize your recognizer here
           # Store any configuration parameters
       
       def predict(
           self, texts: t.List[str]
       ) -> t.List[t.Union[t.List[t.Tuple[int, int]], None]]:
           # Implement your recognition logic here
           # Return list of reference positions for each text
           pass

The ``NAME`` class attribute provides a human-readable identifier for your recognizer. The ``__init__`` method should call the parent initializer with any configuration parameters as keyword arguments. These parameters are automatically stored in the module's configuration and used to generate its unique ID.

The ``predict()`` method receives a list of document texts and must return a list of the same length. For each document, return either a list of ``(start, end)`` tuples representing the character positions of identified place names, or ``None`` if your recognizer cannot process that particular document (for example, if it's in an unsupported language).

Here's a complete example of a simple regex-based recognizer:

.. code-block:: python

   import typing as t
   import re
   from geoparser.modules.recognizers import Recognizer

   class RegexRecognizer(Recognizer):
       """Recognizer that identifies place names using regular expressions."""
       
       NAME = "RegexRecognizer"
       
       def __init__(self, patterns: t.List[str]):
           """
           Initialize with a list of regex patterns.
           
           Args:
               patterns: Regular expressions that match place names
           """
           super().__init__(patterns=patterns)
           self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
       
       def predict(
           self, texts: t.List[str]
       ) -> t.List[t.Union[t.List[t.Tuple[int, int]], None]]:
           """Find all matches of the patterns in each text."""
           results = []
           
           for text in texts:
               references = []
               
               # Find all matches for each pattern
               for pattern in self.patterns:
                   for match in pattern.finditer(text):
                       references.append((match.start(), match.end()))
               
               # Sort by start position and remove overlaps
               references.sort()
               results.append(references)
           
           return results

You can use this custom recognizer just like the built-in ones:

.. code-block:: python

   from geoparser import Project

   # Create recognizer that looks for country names
   recognizer = RegexRecognizer(patterns=[
       r'\b(France|Germany|Italy|Spain|Switzerland)\b',
       r'\b(United States|United Kingdom|New Zealand)\b'
   ])

   project = Project("regex_test")
   project.create_documents(["I traveled from France to Germany."])
   project.run_recognizer(recognizer)

When implementing custom recognizers, ensure that the ``(start, end)`` positions correspond to actual character offsets in the text and that they align with token or entity boundaries when possible. Overlapping references can be problematic for downstream processing, so consider removing or merging them in your implementation.

Creating Custom Resolvers
--------------------------

Custom resolvers follow a similar pattern but implement the ``Resolver`` interface instead. A resolver takes texts and reference positions as input and returns resolved referents (gazetteer name and identifier pairs) for each reference.

The basic structure of a custom resolver:

.. code-block:: python

   import typing as t
   from geoparser.modules.resolvers import Resolver

   class MyCustomResolver(Resolver):
       NAME = "MyCustomResolver"
       
       def __init__(self, gazetteer_name: str, **kwargs):
           super().__init__(gazetteer_name=gazetteer_name, **kwargs)
           self.gazetteer_name = gazetteer_name
           # Initialize your resolver here
       
       def predict(
           self,
           texts: t.List[str],
           references: t.List[t.List[t.Tuple[int, int]]]
       ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
           # Implement your resolution logic here
           # Return list of (gazetteer_name, identifier) tuples
           pass

The ``predict()`` method receives two lists: ``texts`` contains the document texts, and ``references`` contains the reference positions for each document. The method must return a nested list with the same structure as ``references``, where each element is either a ``(gazetteer_name, identifier)`` tuple pointing to a feature in the gazetteer, or ``None`` if that reference could not be resolved.

Resolvers typically interact with gazetteers to find candidate locations. The library provides the ``Gazetteer`` class for this purpose:

.. code-block:: python

   import typing as t
   from geoparser.modules.resolvers import Resolver
   from geoparser import Gazetteer

   class PopulationResolver(Resolver):
       """Resolver that selects the most populous candidate."""
       
       NAME = "PopulationResolver"
       
       def __init__(self, gazetteer_name: str = "geonames"):
           super().__init__(gazetteer_name=gazetteer_name)
           self.gazetteer_name = gazetteer_name
           self.gazetteer = Gazetteer(gazetteer_name)
       
       def predict(
           self,
           texts: t.List[str],
           references: t.List[t.List[t.Tuple[int, int]]]
       ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
           """Resolve each reference to the most populous candidate."""
           results = []
           
           for text, doc_refs in zip(texts, references):
               doc_results = []
               
               for start, end in doc_refs:
                   reference_text = text[start:end]
                   
                   # Search for candidates
                   candidates = self.gazetteer.search(
                       reference_text,
                       method="partial",
                       limit=100
                   )
                   
                   if candidates:
                       # Select candidate with highest population
                       best = max(
                           candidates,
                           key=lambda c: c.data.get('population', 0) or 0
                       )
                       doc_results.append(
                           (self.gazetteer_name, best.location_id_value)
                       )
                   else:
                       doc_results.append(None)
               
               results.append(doc_results)
           
           return results

The ``Gazetteer`` class provides two main methods for retrieving candidates. The ``search()`` method takes a place name string and returns matching features using the specified search method (``"exact"``, ``"phrase"``, ``"partial"``, or ``"fuzzy"``). The ``find()`` method looks up a feature by its identifier. See the :doc:`gazetteers` guide for more details on working with gazetteers.

When implementing custom resolvers, always handle the case where no candidates are found by returning ``None`` for that reference. Make sure the returned structure exactly matches the input ``references`` structure—each document should have the same number of results as it has references, and they should be in the same order.

Making Modules Trainable
-------------------------

If you want your custom modules to be trainable, implement a ``fit()`` method with the appropriate interface. For recognizers, the ``fit()`` method should accept texts and reference positions:

.. code-block:: python

   def fit(
       self,
       texts: t.List[str],
       references: t.List[t.List[t.Tuple[int, int]]],
       **kwargs
   ) -> None:
       """Train the recognizer on annotated data."""
       # Implement your training logic here
       pass

For resolvers, the ``fit()`` method should additionally accept referents:

.. code-block:: python

   def fit(
       self,
       texts: t.List[str],
       references: t.List[t.List[t.Tuple[int, int]]],
       referents: t.List[t.List[t.Optional[t.Tuple[str, str]]]],
       **kwargs
   ) -> None:
       """Train the resolver on annotated data."""
       # Implement your training logic here
       pass

The ``fit()`` method can accept additional keyword arguments for training parameters like learning rate, batch size, or number of epochs. Once implemented, your custom modules can be trained using the project-level training methods described in the :doc:`training` guide.

Next Steps
----------

Now that you understand the module system, you can explore:

- :doc:`training` - Learn how to fine-tune recognizers and resolvers on your own data
- :doc:`gazetteers` - Understand how to work with geographic databases
- :doc:`projects` - Use modules in project-based workflows

For complete API documentation of module classes, see the :doc:`../api/modules` reference.

