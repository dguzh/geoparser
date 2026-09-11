# Use a lazy-loading approach to avoid importing all modules
from importlib import import_module
from types import ModuleType

# Define a mapping of module classes to their import paths
_MODULE_PATHS = {
    "GLiNER2Recognizer": "geoparser.modules.recognizers.gliner",
    "SpacyRecognizer": "geoparser.modules.recognizers.spacy",
    "JinaResolver": "geoparser.modules.resolvers.jina",
    "SentenceTransformerResolver": "geoparser.modules.resolvers.sentencetransformer",
}


def __getattr__(name):
    """Lazy-load modules only when they are accessed."""
    if name in _MODULE_PATHS:
        module = import_module(_MODULE_PATHS[name])
        return getattr(module, name)
    raise AttributeError(f"module 'geoparser.modules' has no attribute '{name}'")
