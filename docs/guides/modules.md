# Configuring Modules

Modules are the interchangeable parts of a pipeline. This guide covers the two built-in ones, the parameters that matter when your results are disappointing, and how to write your own.

## What a Module Is

There are two kinds. A **recognizer** finds place names in text: it takes texts and returns character positions. A **resolver** links those names to places: it takes texts and positions and returns gazetteer entries. Each is written independently of the other, and a pipeline is one of each.

That is the whole interface, and it is deliberately small. A module receives text and returns predictions; everything else — storing results, avoiding duplicate work, keeping different runs apart — happens outside it. The practical consequence is that writing a module is a modest job: implement one method, and it works everywhere the built-in ones do. Full signatures for every module are in the [modules API](../api/modules.md) reference.

One behavior follows from this and is worth knowing early. A module is identified by its class **together with its configuration**. `SpacyRecognizer()` and `SpacyRecognizer(model_name="en_core_web_trf")` are two different modules as far as the library is concerned, with separate results. That is what makes it safe to run a pipeline repeatedly without redoing work, and what makes comparing configurations possible — but it also means changing a parameter does not update your old results, it produces new ones alongside them.

## Built-in Recognizers

### GLiNER2Recognizer

The `GLiNER2Recognizer` uses [GLiNER2.5](https://huggingface.co/fastino/gliner2.5-multi-v1), a zero-shot extractor: the entity types it looks for are given as ordinary words at call time rather than baked into the model. That makes it multilingual out of the box, and it makes the label list a parameter you can tune for your corpus instead of a fixed schema you have to live with.

To use it with default settings:

``` python
from geoparser.modules import GLiNER2Recognizer

recognizer = GLiNER2Recognizer()
```

The default configuration uses the `fastino/gliner2.5-multi-v1` checkpoint and looks for `city`, `country` and `location`. Both are configurable:

``` python
from geoparser.modules import GLiNER2Recognizer

recognizer = GLiNER2Recognizer(
    entity_types=["city", "country", "river", "mountain", "national park"],
)
```

Because the labels are matched zero-shot, naming what you actually want is usually more effective than reaching for a bigger model. If your corpus is about hiking routes, asking for `mountain` and `trail` will find things no fixed GPE/LOC/FAC schema exposes. The trade-off is that each extra label costs inference time, and overlapping labels are deduplicated: a span found under both `city` and `country` is one reference, not two.

Spans from every label are merged into a single list ordered by position in the text, so the resolver sees the references in the order they are written.

### SpacyRecognizer

The `SpacyRecognizer` uses spaCy's named entity recognition capabilities to identify potential place names in text. By default, it recognizes entities labeled as geopolitical entities (GPE), locations (LOC), and facilities (FAC) as potential toponyms, though this can be customized.

To use the SpacyRecognizer with default settings:

``` python
from geoparser.modules import SpacyRecognizer

recognizer = SpacyRecognizer()
```

The default configuration uses the `en_core_web_sm` model and recognizes entities of types FAC, GPE, and LOC. You can customize both of these parameters:

``` python
from geoparser.modules import SpacyRecognizer

# Use a more accurate transformer-based model
recognizer = SpacyRecognizer(
    model_name="en_core_web_trf",
    entity_types=["GPE", "LOC"],  # Only geopolitical entities and locations
)
```

The `model_name` parameter accepts any spaCy model that includes a named entity recognizer. Larger models like `en_core_web_trf` provide higher accuracy but require more memory and processing time. For non-English texts, specify an appropriate spaCy model for that language.

Transformer pipelines such as `en_core_web_trf` are built on the `curated_transformer` component, which comes from the `spacy-curated-transformers` plugin. Geoparser installs that plugin for you, except on Python 3.14 and later, where it has no release yet; there the transformer models cannot be loaded and `en_core_web_lg` is the most accurate option.

The `entity_types` parameter allows you to filter which entity types are considered as toponyms. By default, the recognizer includes FAC (facilities like buildings and landmarks), GPE (geopolitical entities like countries and cities), and LOC (natural locations and regions). If your application only needs to identify country and city names, you might restrict this to just GPE.

## Built-in Resolvers

### JinaResolver

The `JinaResolver` extends the `SentenceTransformerResolver` below and changes how a candidate is chosen. It keeps the same tiered gazetteer search and the same context windowing, and differs in two ways.

First, it embeds with [jina-embeddings-v5-text-small](https://huggingface.co/jinaai/jina-embeddings-v5-text-small), which has **separate prompts for the two sides of a retrieval pair**. A reference's context is embedded as a query and a candidate's description as a document, which is what the model was trained for; embedding both under one prompt throws away most of the benefit.

Second, it adds a **reranking stage**. The embedding comparison is cheap but sees each side in isolation, so it is used only to shortlist. [jina-reranker-v3.5](https://huggingface.co/jinaai/jina-reranker-v3.5) — a cross encoder, which reads the context and the candidate description together — then picks the winner from that shortlist.

``` python
from geoparser.modules import JinaResolver

resolver = JinaResolver()
```

The defaults are the two checkpoints named above, a shortlist of 20 candidates, the `geonames` gazetteer, a minimum similarity of 0.6 and up to 3 search tiers. The parameters specific to this resolver are:

``` python
from geoparser.modules import JinaResolver

resolver = JinaResolver(
    rerank_top_k=50,  # rerank more candidates, more slowly
    gazetteer_name="swissnames3d",
)
```

`rerank_top_k` is the knob worth understanding. The cross encoder is far more expensive per candidate than the embedding comparison, so the shortlist is what keeps resolution affordable; widening it helps when the right candidate is being ranked outside the top 20 by embeddings alone, and costs proportionally more time. `min_similarity` still gates the embedding stage: a reference whose best candidate does not reach it is left unresolved and the reranker is never consulted.

### SentenceTransformerResolver

The `SentenceTransformerResolver` uses transformer-based language models to disambiguate place names by comparing contextual embeddings. It extracts the context surrounding each place name, retrieves candidate locations from the gazetteer, generates textual descriptions of these candidates, and selects the candidate whose description most closely matches the context based on embedding cosine similarity.

To use the SentenceTransformerResolver with default settings:

``` python
from geoparser.modules import SentenceTransformerResolver

resolver = SentenceTransformerResolver()
```

The default configuration uses the `dguzh/geo-all-MiniLM-L6-v2` model with the `geonames` gazetteer, a minimum similarity threshold of 0.6, and expands through up to 3 tiers of increasingly broad search methods. You can customize any of these parameters:

``` python
from geoparser.modules import SentenceTransformerResolver

# Use a more accurate model with Swiss gazetteer
resolver = SentenceTransformerResolver(
    model_name="dguzh/geo-all-distilroberta-v1",
    gazetteer_name="swissnames3d",
    min_similarity=0.5,  # Accept more candidates
    max_tiers=2,  # Search through fewer tiers for faster processing
)
```

The `model_name` parameter specifies which SentenceTransformer model to use for generating embeddings. The library provides two pre-trained models fine-tuned for toponym disambiguation: `dguzh/geo-all-MiniLM-L6-v2` offers fast processing with good accuracy, while `dguzh/geo-all-distilroberta-v1` provides higher accuracy at the cost of speed and memory. These models were trained on English news articles and work best with English text and the GeoNames gazetteer. For other languages or domains, you should train a custom model as described in the [training](training.md) guide.

The `gazetteer_name` parameter determines which geographic database to search. The specified gazetteer must be installed on your system. Each gazetteer has different coverage and attribute schemas, so make sure your application requirements match the gazetteer's capabilities.

The `min_similarity` threshold controls how confident the resolver must be before accepting a match. Higher thresholds reduce false positives but may leave more toponyms unresolved. Lower thresholds resolve more toponyms but may introduce incorrect matches. If no candidates meet this threshold, the toponym remains unresolved (preserving precision over recall).

The `max_tiers` parameter controls how aggressively the resolver searches for candidates. The resolver uses an iterative strategy starting with exact string matching and progressively relaxing to phrase matching, partial matching, and fuzzy matching. For each search method, it ranks results by relevance and groups them into tiers. The `max_tiers` parameter determines how many of these tiers to include—higher values mean the resolver expands its search to include more potential candidates, which can help resolve difficult toponyms but increases processing time.

The `attribute_map` parameter tells the resolver how to read the gazetteer's attributes. Before comparing a candidate place against the text, this resolver describes the candidate in words — "Paris (city) in Île-de-France, France" — and since every gazetteer names its attributes differently, it needs to be told which ones that sentence is built from. The resolver already knows the mapping for GeoNames and SwissNames3D, so it only has to be passed for a gazetteer of your own:

``` python
from geoparser.modules import SentenceTransformerResolver

resolver = SentenceTransformerResolver(
    gazetteer_name="my_gazetteer",
    attribute_map={
        "name": "place_name",
        "type": "category",
        "level1": "country",
        "level2": "region",
        "level3": "district",
    },
)
```

The values are keys of your gazetteer's `data` dictionary, and which keys exist is decided when the gazetteer is configured (see [custom gazetteers](custom-gazetteers.md)). `name` and `type` are both required. The administrative levels are optional, with `level1` the outermost enclosing place and `level3` the innermost; supply only as many as your data supports. A gazetteer of ancient places, for example, may have nothing above the Roman province a place falls in:

``` python
resolver = SentenceTransformerResolver(
    gazetteer_name="pleiades",
    attribute_map={
        "name": "title",
        "type": "place_types",
        "level1": "province",
    },
)
```

That map describes a candidate as "Pompeii (settlement, urban area) in Italia". Keys that are missing from a feature's `data` are left out of its description rather than failing, so a mapping may name an attribute that only some of your features carry.

Bear in mind that the pre-trained models are fine-tuned on GeoNames-style descriptions. Against a gazetteer whose vocabulary is very different, expect to lower `min_similarity` and, for the best results, to fine-tune a resolver of your own on data annotated with that gazetteer's features — see [training](training.md).

The SentenceTransformerResolver works best when place names have distinctive contexts that help disambiguate them. For example, "I visited the Eiffel Tower in Paris" provides strong contextual clues. Short texts with minimal context or lists of place names without surrounding text present more challenging scenarios where the resolver may struggle.

## Creating Custom Recognizers

You can create custom recognizers by implementing the `Recognizer` interface. A recognizer is a class that inherits from `Recognizer` and implements a `predict()` method that takes a list of texts and returns predictions for each text.

The basic structure of a custom recognizer looks like this:

``` python
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
```

The `NAME` class attribute provides a human-readable identifier for your recognizer. The `__init__` method should call the parent initializer with any configuration parameters as keyword arguments. These parameters are automatically stored in the module's configuration and used to generate its unique ID.

The `predict()` method receives a list of document texts and must return a list of the same length. For each document, return either a list of `(start, end)` tuples representing the character positions of identified place names, or `None` if your recognizer cannot process that particular document (for example, if it's in an unsupported language).

Here's a complete example of a simple regex-based recognizer:

``` python
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
```

You can use this custom recognizer just like the built-in ones:

``` python
from geoparser import Project

# Create recognizer that looks for country names
recognizer = RegexRecognizer(
    patterns=[
        r"\b(France|Germany|Italy|Spain|Switzerland)\b",
        r"\b(United States|United Kingdom|New Zealand)\b",
    ]
)

project = Project("regex_test")
project.create_documents(["I traveled from France to Germany."])
project.run_recognizer(recognizer)
```

When implementing custom recognizers, ensure that the `(start, end)` positions correspond to actual character offsets in the text and that they align with token or entity boundaries when possible. Overlapping references can be problematic for downstream processing, so consider removing or merging them in your implementation.

## Creating Custom Resolvers

Custom resolvers follow a similar pattern but implement the `Resolver` interface instead. A resolver takes texts and reference positions as input and returns resolved referents (gazetteer name and identifier pairs) for each reference.

The basic structure of a custom resolver:

``` python
import typing as t
from geoparser.modules.resolvers import Resolver


class MyCustomResolver(Resolver):
    NAME = "MyCustomResolver"

    def __init__(self, gazetteer_name: str, **kwargs):
        super().__init__(gazetteer_name=gazetteer_name, **kwargs)
        self.gazetteer_name = gazetteer_name
        # Initialize your resolver here

    def predict(
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        # Implement your resolution logic here
        # Return list of (gazetteer_name, identifier) tuples
        pass
```

The `predict()` method receives two lists: `texts` contains the document texts, and `references` contains the reference positions for each document. The method must return a nested list with the same structure as `references`, where each element is either a `(gazetteer_name, identifier)` tuple pointing to a feature in the gazetteer, or `None` if that reference could not be resolved.

Resolvers typically interact with gazetteers to find candidate locations. The library provides the `Gazetteer` class for this purpose:

``` python
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
        self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]]
    ) -> t.List[t.List[t.Union[t.Tuple[str, str], None]]]:
        """Resolve each reference to the most populous candidate."""
        results = []

        for text, doc_refs in zip(texts, references):
            doc_results = []

            for start, end in doc_refs:
                reference_text = text[start:end]

                # Search for candidates
                candidates = self.gazetteer.search(
                    reference_text, method="partial", limit=100
                )

                if candidates:
                    # Select candidate with highest population
                    best = max(
                        candidates, key=lambda c: c.data.get("population", 0) or 0
                    )
                    doc_results.append((self.gazetteer_name, best.identifier))
                else:
                    doc_results.append(None)

            results.append(doc_results)

        return results
```

The `Gazetteer` class provides two main methods for retrieving candidates. The `search()` method takes a place name string and returns matching features using the specified search method (`"exact"`, `"phrase"`, `"partial"`, or `"fuzzy"`). The `find()` method looks up a feature by its identifier. See the `gazetteers` guide for more details on working with gazetteers.

When implementing custom resolvers, always handle the case where no candidates are found by returning `None` for that reference. Make sure the returned structure exactly matches the input `references` structure—each document should have the same number of results as it has references, and they should be in the same order.

## Making Modules Trainable

If you want your custom modules to be trainable, implement a `fit()` method with the appropriate interface. For recognizers, the `fit()` method should accept texts and reference positions:

``` python
def fit(
    self, texts: t.List[str], references: t.List[t.List[t.Tuple[int, int]]], **kwargs
) -> None:
    """Train the recognizer on annotated data."""
    # Implement your training logic here
    pass
```

For resolvers, the `fit()` method should additionally accept referents:

``` python
def fit(
    self,
    texts: t.List[str],
    references: t.List[t.List[t.Tuple[int, int]]],
    referents: t.List[t.List[t.Optional[t.Tuple[str, str]]]],
    **kwargs,
) -> None:
    """Train the resolver on annotated data."""
    # Implement your training logic here
    pass
```

The `fit()` method can accept additional keyword arguments for training parameters like learning rate, batch size, or number of epochs. Once implemented, your custom modules can be trained using the project-level training methods described in the [training](training.md) guide.
