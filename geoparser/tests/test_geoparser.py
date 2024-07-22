from contextlib import nullcontext

import pytest
import spacy
from sentence_transformers import SentenceTransformer

from geoparser import constants as C
from geoparser.gazetteer import Gazetteer
from geoparser.geodoc import GeoDoc
from geoparser.geoparser import Geoparser


@pytest.fixture
def geoparser() -> Geoparser:
    geoparser = Geoparser(
        spacy_model="en_core_web_sm",
        transformer_model="dguzh/geo-all-MiniLM-L6-v2",
        gazetteer="geonames",
    )
    return geoparser


@pytest.mark.parametrize("gazetteer", list(C.GAZETTEERS.keys()) + ["non_existing"])
def test_init_geoparser_gazetteers(gazetteer: str):
    # can be instantiated with all supported gazetteers
    with nullcontext() if gazetteer != "non_existing" else pytest.raises(ValueError):
        _ = Geoparser(
            spacy_model="en_core_web_sm",
            transformer_model="dguzh/geo-all-MiniLM-L6-v2",
            gazetteer=gazetteer,
        )


@pytest.mark.parametrize("spacy_model", ["en_core_web_sm", "en_core_web_trf"])
def test_init_geoparser_spacy_model(spacy_model: str):
    # raises error if spacy model has not been installed yet
    with nullcontext() if spacy_model == "en_core_web_sm" else pytest.raises(OSError):
        _ = Geoparser(
            spacy_model=spacy_model,
            transformer_model="dguzh/geo-all-MiniLM-L6-v2",
            gazetteer="geonames",
        )


@pytest.mark.parametrize("transformer_model", ["dguzh/geo-all-MiniLM-L6-v2", "adfs"])
def test_init_geoparser_transformer_model(transformer_model: str):
    # raises error with unknown transformer_model
    with (
        nullcontext()
        if transformer_model == "dguzh/geo-all-MiniLM-L6-v2"
        else pytest.raises(OSError)
    ):
        _ = Geoparser(
            spacy_model="en_core_web_sm",
            transformer_model=transformer_model,
            gazetteer="geonames",
        )


@pytest.mark.parametrize("gazetteer", list(C.GAZETTEERS.keys()) + ["non_existing"])
def test_setup_gazetteer(geoparser: Geoparser, gazetteer: str):
    with nullcontext() if gazetteer != "non_existing" else pytest.raises(ValueError):
        gazetteer = geoparser.setup_gazetteer(gazetteer)
        assert issubclass(type(gazetteer), Gazetteer)


@pytest.mark.parametrize("spacy_model", ["en_core_web_sm", "en_core_web_trf"])
def test_setup_spacy(geoparser: Geoparser, spacy_model: str):
    with nullcontext() if spacy_model == "en_core_web_sm" else pytest.raises(OSError):
        nlp = geoparser.setup_spacy(spacy_model)
        assert issubclass(type(nlp), spacy.language.Language)


@pytest.mark.parametrize("transformer_model", ["dguzh/geo-all-MiniLM-L6-v2", "adfs"])
def test_setup_transformer(geoparser: Geoparser, transformer_model: str):
    with (
        nullcontext()
        if transformer_model == "dguzh/geo-all-MiniLM-L6-v2"
        else pytest.raises(OSError)
    ):
        model = geoparser.setup_transformer(transformer_model)
        assert isinstance(model, SentenceTransformer)
