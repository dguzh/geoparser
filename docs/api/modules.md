# Modules API

Modules are deliberately small interfaces. Recognizers return reference spans;
resolvers map those spans to gazetteer identifiers.

## Base classes

::: geoparser.modules.recognizers.base.Recognizer

::: geoparser.modules.resolvers.base.Resolver

## Recognizers

::: geoparser.modules.recognizers.gliner.GLiNER2Recognizer

::: geoparser.modules.recognizers.spacy.SpacyRecognizer

## Resolvers

::: geoparser.modules.resolvers.jina.JinaResolver

::: geoparser.modules.resolvers.sentencetransformer.SentenceTransformerResolver

## Context sizing

An encoder truncates anything past its maximum sequence length, so a resolver
has to choose which text around a reference is worth spending that budget on.
That choice is plain arithmetic over sentence costs and lives on its own, with
no dependency on the models that produce those costs.

::: geoparser.modules.resolvers.context
