# Use a lazy-loading approach to avoid importing all modules
from importlib import import_module
from types import ModuleType

# Define a mapping of module classes to their import paths
_MODULE_PATHS = {
    "SpacyRecognizer": "geoparser.modules.recognizers.spacy",
    "ExactRetriever": "geoparser.modules.retrievers.exact",
}


def __getattr__(name):
    """Lazy-load modules only when they are accessed."""
    if name in _MODULE_PATHS:
        module = import_module(_MODULE_PATHS[name])
        return getattr(module, name)
    raise AttributeError(f"module 'geoparser.modules' has no attribute '{name}'")
