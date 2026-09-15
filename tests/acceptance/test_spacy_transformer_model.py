"""
Executable acceptance scenarios for picking a spaCy model.

These read as the experience of a caller following the module guide: the small
model just works, and the transformer model the guide recommends says what is
missing when its plugin is not installed, rather than pointing at the caller's
own code.

spaCy itself is stubbed here, so the scenarios state exactly what they depend
on -- what spacy.load does -- without downloading a half-gigabyte pipeline.
"""

from unittest.mock import Mock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from geoparser.modules.recognizers.spacy import SpacyRecognizer

pytestmark = pytest.mark.acceptance
scenarios("features/spacy_transformer_model.feature")

# What spaCy raises when a pipeline names a component no installed package
# registers; the transformer pipelines name "curated_transformer".
MISSING_FACTORY_ERROR = (
    "[E002] Can't find factory for 'curated_transformer' for language English "
    "(en). This usually happens when spaCy calls `nlp.create_pipe` with a "
    "custom component name that's not registered on the current language class."
)


@pytest.fixture
def model_state() -> dict[str, object]:
    """What each scenario builds up as its steps run."""
    return {}


@given(parsers.parse('the spaCy model "{model_name}" loads'))
def model_loads(model_state: dict[str, object], model_name: str) -> None:
    pipeline = Mock()
    pipeline.pipe_names = ["ner"]
    model_state["load"] = Mock(return_value=pipeline)


@given(
    parsers.parse('the spaCy model "{model_name}" needs the missing transformer plugin')
)
def model_needs_plugin(model_state: dict[str, object], model_name: str) -> None:
    error = ValueError(MISSING_FACTORY_ERROR)
    model_state["spacy_error"] = error
    model_state["load"] = Mock(side_effect=error)


@when(parsers.parse('I build a recognizer on "{model_name}"'))
def build_recognizer(model_state: dict[str, object], model_name: str) -> None:
    with patch("geoparser.modules.recognizers.spacy.spacy.load", model_state["load"]):
        try:
            model_state["recognizer"] = SpacyRecognizer(model_name=model_name)
        except ValueError as error:
            model_state["error"] = error


@then("the recognizer is ready to use")
def recognizer_ready(model_state: dict[str, object]) -> None:
    assert "error" not in model_state
    recognizer = model_state["recognizer"]
    assert isinstance(recognizer, SpacyRecognizer)
    assert recognizer.nlp is not None


@then(parsers.parse('I am told to install "{plugin}"'))
def told_to_install(model_state: dict[str, object], plugin: str) -> None:
    error = model_state["error"]
    assert isinstance(error, ValueError)
    assert plugin in str(error)


@then("I am still shown the original spaCy error")
def original_error_kept(model_state: dict[str, object]) -> None:
    error = model_state["error"]
    assert isinstance(error, ValueError)
    assert "[E002]" in str(error)
    assert error.__cause__ is model_state["spacy_error"]
