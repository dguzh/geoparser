from contextlib import nullcontext

import pytest
import spacy
import torch
from sentence_transformers import SentenceTransformer

from geoparser import constants as C
from geoparser.gazetteer import Gazetteer
from geoparser.geodoc import GeoDoc
from geoparser.geonames import GeoNames
from geoparser.geoparser import Geoparser


@pytest.mark.parametrize("gazetteer", list(C.GAZETTEERS.keys()) + ["non_existing"])
def test_init_geoparser_gazetteers(gazetteer: str):
    # can be instantiated with all supported gazetteers
    with nullcontext() if gazetteer != "non_existing" else pytest.raises(ValueError):
        _ = Geoparser(
            spacy_model="en_core_web_sm",
            transformer_model="dguzh/geo-all-MiniLM-L6-v2",
            gazetteer=gazetteer,
        )


@pytest.mark.parametrize("spacy_model", ["en_core_web_sm", "mk_core_news_sm"])
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


@pytest.mark.parametrize("spacy_model", ["en_core_web_sm", "mk_core_news_sm"])
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


@pytest.mark.parametrize("texts", [("tuple",), [str], ["str"], "str"])
def test_parse(geoparser_real_data: Geoparser, texts):
    with (
        nullcontext()
        if type(texts) is list and all(type(elem) is str for elem in texts)
        else pytest.raises(TypeError)
    ):
        parsed = geoparser_real_data.parse(texts)
        assert type(parsed) is list
        for elem in parsed:
            assert type(elem) is GeoDoc


@pytest.mark.parametrize(
    "texts", [["This is a text.", "This is also a text."], [""], []]
)
def test_recognize(geoparser_real_data: Geoparser, texts):
    parsed = geoparser_real_data.recognize(texts)
    assert type(parsed) is list
    for elem in parsed:
        assert type(elem) is GeoDoc


def test_get_candidate_ids(
    geoparser_real_data: Geoparser,
    geodocs: list[GeoDoc],
    radio_andorra_id: str,
):
    candidate_ids = geoparser_real_data.get_candidate_ids(geodocs)
    assert type(candidate_ids) is list
    for elem in candidate_ids:
        assert type(elem) is str
    assert candidate_ids == [radio_andorra_id]


def test_get_candidate_embeddings_lookup(
    geoparser_real_data: Geoparser, radio_andorra_id: str
):
    candidate_ids = [radio_andorra_id]
    lookup = geoparser_real_data.get_candidate_embeddings_lookup(candidate_ids)
    assert type(lookup) is dict
    for key, value in lookup.items():
        assert type(key) is str
        assert key == radio_andorra_id
        assert type(value) is torch.Tensor


def test_get_toponym_embeddings(geoparser_real_data: Geoparser, geodocs: list[GeoDoc]):
    toponym_embeddings = geoparser_real_data.get_toponym_embeddings(geodocs)
    assert type(toponym_embeddings) is torch.Tensor


def test_resolve_toponym(
    geoparser_real_data: Geoparser,
    geonames_real_data: GeoNames,
    geodocs: list[GeoDoc],
    radio_andorra_id: int,
):
    geoparser_real_data.gazetteer = geonames_real_data
    candidate_ids = geoparser_real_data.get_candidate_ids(geodocs)
    lookup = geoparser_real_data.get_candidate_embeddings_lookup(candidate_ids)
    toponym_embeddings = geoparser_real_data.get_toponym_embeddings(geodocs)
    predicted_id, score = geoparser_real_data.resolve_toponym(
        lookup, candidate_ids, toponym_embeddings, 0
    )
    # roc meler will be matched
    assert predicted_id == radio_andorra_id
    assert type(score) is float


def test_resolve(
    geoparser_real_data: Geoparser,
    geodocs: list[GeoDoc],
    radio_andorra_id: int,
):
    resolved_docs = geoparser_real_data.resolve(geodocs)
    roc_meler = resolved_docs[0].toponyms[0]
    # roc meler will be matched
    assert roc_meler._.loc_id == radio_andorra_id
    assert type(roc_meler._.loc_score) is float
