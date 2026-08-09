# Roadmap

This file collects the larger changes we intend to make to the Irchel Geoparser. They are directions rather than scheduled work, and none of them are needed to use the library as it is today. Feedback on any of them is welcome in the [issue tracker](https://github.com/dguzh/geoparser/issues).

## Modular packaging

`pip install geoparser` currently installs everything: the project layer, the gazetteer subsystem, and a full machine learning stack that exists only to support the two built-in modules. We want the core package to be the architecture itself (the recognizer and resolver interfaces and the machinery around them), with implementations distributed separately.

The gazetteer subsystem is the first candidate for this. Turning arbitrary geographic data into a single-file, uniformly queryable artifact is useful beyond geoparsing, and it should be usable without installing the geoparsing framework alongside it. Resolvers already reach gazetteers only through a small query interface, so the split is mainly a packaging exercise.

The default recognizer and resolver would follow, moving spaCy, PyTorch and Transformers out of a minimal install and leaving lightweight implementations in the core that are sufficient for a complete example. A pipeline now already has to be assembled from modules explicitly, so no part of the library silently assumes that a particular implementation is installed.

## Data handling

Results are currently persisted in a database, and even the simple parse interface goes through a project under the hood. Persistence is genuinely useful for comparing runs over the same material, but we now think making it the core data model is the wrong default for an NLP library. Tools in this space are usually pipeline-shaped: text goes in, annotations come out, and persistence is left to the user.

We intend to rethink input and output along those lines. Toponym annotations and texts are usually lightweight, so an in-memory representation is likely practical even for sizeable corpora, with a database becoming one optional backend rather than the pipeline itself.
