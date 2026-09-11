# Architecture

The package is organized around a small, explicit pipeline:

```text
text → recognizer → reference spans → resolver → gazetteer features
```

`Geoparser` is the stateless entry point. `Project` adds persistence and
repeatable comparison of result sets. Recognizers and resolvers implement
independent interfaces, while services coordinate those interfaces with the
database.

## Dependency boundaries

The import direction is intentionally one-way:

```text
modules → (no database or project imports)
services → modules, database
project → services, context, database
gazetteer → artifact and build internals
```

The executable architecture checker in
[`scripts/check_architecture.py`](https://github.com/NoeFlandre/geoparser/blob/main/scripts/check_architecture.py)
rejects forbidden layer imports and import cycles. `TYPE_CHECKING` imports are
ignored because they do not create runtime coupling.

## Side effects

Model inference, network access, filesystem access, and database writes stay at
the edges of the system. Pure matching helpers and module contracts can be
tested without a database or downloaded model. Integration and acceptance
tests use deterministic fixtures for the boundaries that must be exercised
together.

## Extension point

To add a recognizer or resolver, implement the corresponding base interface,
keep configuration in the module identity, and avoid reaching through the
database layer. The [modules guide](guides/modules.md) shows the complete
contract and examples.
