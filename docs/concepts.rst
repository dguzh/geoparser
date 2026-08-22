.. _concepts:

Concepts
========

This page explains the ideas the library is built on, and the terms used throughout the rest of the documentation. It contains no code.

The Problem
-----------

Text is full of places. A news archive, a corpus of interviews, a collection of travel diaries, a set of historical records — all of them refer constantly to where things happened. But that geography is locked up in prose. You cannot map it, count it, or join it to anything else, because as far as a computer is concerned "Basel" is just five letters.

**Geoparsing** is the process of turning those mentions into geographic data. Give it a text, and it gives you back a list of the places the text mentions, each one tied to a specific point or area on the earth.

It is conventionally split into two problems, because they are genuinely different problems.

Recognition: which words are places?
------------------------------------

The first task is finding the place names. In

    *The delegation flew from Basel to Santiago in March.*

a human sees immediately that "Basel" and "Santiago" are places and "March" is not, even though all three are capitalized. Doing this automatically is a well-studied problem in natural language processing called **named entity recognition**, and a *toponym* — the technical term for a place name — is one kind of named entity.

This is harder than matching against a list of known place names, for two reasons. Many place names are also ordinary words or other kinds of name: Reading is a town and a verb, Jordan is a country and a surname, Turkey is a country and a bird. And a list can never be complete. So recognition works from **context** — the grammar and vocabulary around a word — rather than from a lookup. Approaches to it range from hand-written rules to statistical and neural models; today it is usually done with a trained language model, which is also why it can fail on text unlike what that model was trained on.

In this library, recognition is the job of a **recognizer**. Its output is a set of character positions: spans of the text that appear to be place names. Nothing geographic has happened yet.

Resolution: which place is it?
------------------------------

The second task is deciding *which* place each name refers to.

GeoNames records 122 places called Paris, 45 of them in the United States, and 291 called Springfield. When a text says "Santiago", it may mean the capital of Chile, one of several cities in Cuba or Spain, or a person. Choosing correctly is called **toponym resolution**, or sometimes toponym disambiguation or geocoding.

Again, the answer is in the context. Consider:

    *The delegation flew from Basel to Santiago in March.*

    *Pilgrims have walked to Santiago for a thousand years.*

The same name, two different cities — and you knew which was which from the surrounding words, not from the name. The second sentence's "pilgrims" and "thousand years" point at Santiago de Compostela in Spain; nothing in the first sentence does, and Chile's capital is the more prominent city.

A **resolver** does this. For each recognized name it looks up the candidates, weighs them against the context of the mention, and picks one — or picks none, if nothing is convincing enough. That last possibility matters: the library's default resolver leaves a toponym unresolved when no candidate passes its similarity threshold, so unresolved toponyms are a normal part of the output.

Gazetteers: the list of candidates
----------------------------------

To choose between candidate places, you need a list of the places that exist. That is a **gazetteer**: a database of places, where each entry has

- a stable **identifier**,
- one or more **names** it is known by, including historical and foreign-language forms,
- usually a **location** — a point, or an area,
- and a set of **attributes**: what kind of place it is, what it contains or is contained by, how many people live there, and so on.

Those attributes are what makes resolution possible at all. GeoNames describes one Santiago as the capital of Chile with 4.8 million inhabitants, and another as the seat of a Spanish region, in Galicia, with about 100,000 — and it is against descriptions like those that a resolver weighs the words surrounding a mention. What a gazetteer records is fairly plain factual data of this kind; it will not tell you that one of these cities is a pilgrimage destination, so a mention that can only be identified from knowledge the gazetteer does not hold is a genuinely hard case.

This is why installing a gazetteer is a required setup step in this library and not a detail. Recognition works on text alone, but resolving a name to a place here means selecting an entry from a gazetteer, so there has to be one to select from. It is not the only way the problem can be approached — there are methods that predict coordinates directly from the words, without a list of candidate places — but selecting from a gazetteer is what this library does, and it is what gives you an identifier and attributes rather than a coordinate pair alone.

It is also why the choice of gazetteer shapes your results more than any other single decision: a gazetteer containing only cities cannot resolve a river, and one covering only the modern world cannot resolve a Roman province, no matter how good the models are. :doc:`guides/gazetteers` describes what the pre-configured gazetteers contain, and if neither of them describes the world you are studying, you can build one from your own data — see :ref:`custom-gazetteers`.

Putting It Together
-------------------

A pipeline in this library is two stages in sequence: text goes to the recognizer, which returns the spans of the place names it found; those spans and the text then go to the resolver, which returns the place each name refers to. The gazetteer is not a third stage but the resource the resolver consults, and it belongs to the resolver — which is told at construction time which gazetteer to use.

Both modules are stated explicitly when you build a ``Geoparser``, and there are no defaults for either.

That explicitness is deliberate. The two stages are independent, and separating them is the library's central design decision. It means you can change how names are found without touching how they are resolved, compare two recognizers against the same resolver to see which finds more, give a resolver a different gazetteer, or replace either stage with an implementation of your own — :doc:`guides/modules` covers the modules that exist and how to write one. It also means the two stages can fail independently, which is worth remembering when a result looks wrong: if nothing comes back, check first whether anything was recognized, since a resolver cannot resolve a name a recognizer never found.

What Comes Out
--------------

Results are shaped like the pipeline that produced them.

A **document** is one text you put in. Each document has **toponyms** — the place names found in it. Each toponym knows its ``text`` and where it sits in the document (``start`` and ``end`` character offsets), which is how you get back to the surrounding sentence. And each toponym has a ``location``: the gazetteer entry it was resolved to, or ``None`` if it was not resolved.

A location is a **feature**: one entry in a gazetteer. It carries the gazetteer's ``data`` for that place as a dictionary, and its ``geometry`` as a shape you can map, measure, or export. Because gazetteers differ, so do the available attributes — GeoNames calls a place's name ``name``, SwissNames3D calls it ``NAME`` — so read them defensively rather than assuming.

Two Ways to Work
----------------

The library offers two entry points for the same pipeline, and the difference is only whether results are kept.

``Geoparser`` is the direct one: text in, documents out, nothing stored. Use it for analysis you run in one sitting, in a script or a notebook, where the results go straight into whatever you do next. This is what the :doc:`quickstart` uses, and the one to start with.

``Project`` is a persistent workspace. Documents and results are stored in a database under a name, so you can process a corpus once, come back next week, and still have the results — and, more importantly, run several different pipelines over the same corpus and keep all of their outputs side by side under different **tags**. That is what makes systematic comparison possible: same texts, different configurations, results that can be counted against each other. Use it for corpus research, for building and evaluating annotated data, and for results you would not want to recompute. See :doc:`guides/projects`.

Start with ``Geoparser``. Move to ``Project`` when you find yourself wanting to keep something.

.. note::

   ``Geoparser`` is the interface we expect to remain stable. The database-backed project layer is likely to become one option among several rather than the foundation everything sits on.

Words You Will See
------------------

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Term
     - Meaning
   * - **Toponym**
     - A place name as it appears in text. "Basel" in a sentence is a toponym; the city itself is not.
   * - **Reference**
     - This library's name for a recognized toponym: a span of text identified as a place name. ``document.toponyms`` returns these.
   * - **Referent**
     - The place a reference actually points to. Recorded as a gazetteer name and an identifier.
   * - **Feature**
     - One entry in a gazetteer — a place, with its names, attributes, and geometry. What ``toponym.location`` gives you.
   * - **Recognition**
     - Finding place names in text. Stage one.
   * - **Resolution**
     - Deciding which place each name refers to. Stage two. Also called disambiguation or geocoding.
   * - **Gazetteer**
     - A database of places used as the candidate set for resolution.
   * - **Module**
     - A recognizer or a resolver. The interchangeable parts of a pipeline.
   * - **Tag**
     - A label identifying one pipeline's results within a project, so several can coexist over the same documents.
   * - **Artifact**
     - The single self-contained file an installed gazetteer consists of.
