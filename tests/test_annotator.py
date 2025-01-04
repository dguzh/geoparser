import types
import typing as t

import pytest
from fastapi import UploadFile
from markupsafe import Markup
from werkzeug.datastructures import FileStorage

from geoparser.annotator.annotator import GeoparserAnnotator
from geoparser.gazetteers import GeoNames
from tests.utils import get_static_test_file


@pytest.fixture(scope="function")
def annotator(geonames_real_data: GeoNames) -> GeoparserAnnotator:
    annotator = GeoparserAnnotator()
    annotator.gazetteer = geonames_real_data
    return annotator


@pytest.fixture(scope="session")
def geonames_filter_attributes() -> list[str]:
    return [
        "name",
        "feature_type",
        "admin2_name",
        "admin1_name",
        "country_name",
    ]


@pytest.mark.parametrize("query", [(0, 7), (22, 23)])
def test_get_toponym(annotator: GeoparserAnnotator, query: tuple[int, int]):
    start, end = query
    toponyms = [
        {
            "text": "AndoRra",
            "start": 0,
            "end": 7,
            "loc_id": "",
        },
        {
            "text": "Andorra",
            "start": 0,
            "end": 7,
            "loc_id": "",
        },
    ]
    result = annotator.get_toponym(toponyms, start, end)
    if query == (0, 7):  # matches toponym
        assert (
            result == toponyms[0]
        )  # always return first toponym with given start and end
    else:
        assert result is None


@pytest.mark.parametrize("apply_spacy", [True, False])
def test_parse_files(annotator: GeoparserAnnotator, apply_spacy: bool):
    model = "en_core_web_sm"
    with open(get_static_test_file("annotator_doc0.txt"), "rb") as doc1, open(
        get_static_test_file("annotator_doc1.txt"), "rb"
    ) as doc2:
        documents = {0: doc1, 1: doc2}
        result = annotator.parse_files(
            [
                UploadFile(
                    file=FileStorage(stream=documents[i]),
                    filename=f"annotator_doc{i}.txt",
                )
                for i in range(2)
            ],
            model,
            apply_spacy,
        )
        assert type(result) is types.GeneratorType
        result = list(result)
        assert len(result) == 2
        for i, elem in enumerate(result):
            assert type(elem) is dict
            assert elem["filename"] == f"annotator_doc{i}.txt"
            assert elem["spacy_model"] == model
            assert elem["spacy_applied"] == apply_spacy
            documents[i].seek(0)
            assert elem["text"] == documents[i].read().decode("utf-8")
            n_toponyms = len(elem["toponyms"])
            assert n_toponyms == 1 if apply_spacy else n_toponyms == 0
            for toponym in elem["toponyms"]:
                for key in ["text", "start", "end", "loc_id"]:
                    assert key in toponym
                assert (
                    elem["text"][toponym["start"] : toponym["end"]] == toponym["text"]
                )


def test_parse_doc(annotator: GeoparserAnnotator):
    doc = {
        "filename": "test.txt",
        "spacy_model": "en_core_web_sm",
        "text": "Canada is a nice place.",
        "toponyms": [],
        "spacy_applied": False,
    }
    result = annotator.parse_doc(doc)
    assert result["spacy_applied"] is True
    assert len(result["toponyms"]) == 1
    toponym = result["toponyms"][0]
    assert toponym["text"] == "Canada"
    assert toponym["start"] == 0
    assert toponym["end"] == 6
    assert toponym["loc_id"] == ""


@pytest.mark.parametrize(
    "old_toponyms,new_toponyms,expected",
    [
        (
            [],
            [],
            [],
        ),
        (
            [],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                }
            ],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                }
            ],
        ),
        (
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                }
            ],
            [],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                }
            ],
        ),
        (
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "42",
                }
            ],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                }
            ],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "42",
                }
            ],
        ),
        (
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "41",
                }
            ],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "",
                },
                {
                    "text": "test2",
                    "start": 3,
                    "end": 4,
                    "loc_id": "",
                },
            ],
            [
                {
                    "text": "test1",
                    "start": 0,
                    "end": 1,
                    "loc_id": "41",
                },
                {
                    "text": "test2",
                    "start": 3,
                    "end": 4,
                    "loc_id": "",
                },
            ],
        ),
    ],
)
def test_merge_toponyms(
    annotator: GeoparserAnnotator,
    old_toponyms: list[dict],
    new_toponyms: list[dict],
    expected: list[dict],
):
    result = annotator.merge_toponyms(old_toponyms, new_toponyms)
    assert result == expected


def test_get_pre_annotated_text(annotator: GeoparserAnnotator):
    text = "Andorra is a nice place."
    toponyms = [
        {
            "text": "Andorra",
            "start": 0,
            "end": 7,
            "loc_id": "",
        }
    ]
    result = annotator.get_pre_annotated_text(text, toponyms)
    assert result == Markup(
        '<span class="toponym " data-start="0" data-end="7">Andorra</span> is a nice place.'
    )


@pytest.mark.parametrize("annotation", ["", "3039332"])
def test_prepare_documents(annotator: GeoparserAnnotator, annotation: str):
    documents = [
        {
            "filename": "andorra.txt",
            "spacy_model": "en_core_web_sm",
            "text": "Andorra is a nice place.",
            "toponyms": [
                {"text": "Andorra", "start": 0, "end": 7, "loc_id": annotation}
            ],
        }
    ]
    result = annotator.prepare_documents(documents)
    assert type(result) is types.GeneratorType
    result = list(result)
    assert len(result) == 1
    assert result[0] == {
        "filename": documents[0]["filename"],
        "total_toponyms": 1,
        "annotated_toponyms": 1 if annotation else 0,
        "doc_index": 0,
    }


@pytest.mark.parametrize(
    "toponym,expected",
    [
        (
            {
                "text": "Andorra",
                "start": 0,
                "end": 7,
                "loc_id": "",
            },
            "",
        ),
        (
            {
                "text": "Andorra",
                "start": 0,
                "end": 7,
            },
            "",
        ),
        (
            {
                "text": "Andorra",
                "start": 0,
                "end": 7,
                "loc_id": "3039332",
            },
            "3039332",
        ),
    ],
)
def test_get_existing_loc_id(
    annotator: GeoparserAnnotator, toponym: dict[str, str], expected: str
):
    assert annotator.get_existing_loc_id(toponym) == expected


@pytest.mark.parametrize("loc_id", ["", "3039332"])
@pytest.mark.parametrize("crs", ["EPSG:4326", "EPSG:2056"])
@pytest.mark.parametrize("coordinates", [None, 0.0, 1 + 9j])
def test_get_candidate_descriptions(
    annotator: GeoparserAnnotator,
    loc_id: str,
    radio_andorra_id: str,
    crs: str,
    coordinates: t.Optional[float],
    monkeypatch,
):
    # monkeypatch query_locations to return different coordinates
    monkeypatched_radio_andorra = {
        "geonameid": str(radio_andorra_id),
        "name": "Radio Andorra",
        "feature_type": "radio station",
        "latitude": coordinates,
        "longitude": coordinates,
        "elevation": None,
        "population": 0,
        "admin2_geonameid": None,
        "admin2_name": None,
        "admin1_geonameid": "3040684",
        "admin1_name": "Encamp",
        "country_geonameid": "3041565",
        "country_name": "Andorra",
    }
    monkeypatch.setattr(
        GeoNames,
        "query_locations",
        lambda *args, **kwargs: [monkeypatched_radio_andorra],
    )
    toponym = {
        "text": "Andorra",
        "start": 0,
        "end": 7,
        "loc_id": loc_id,
    }
    toponym_text = "Andorra"
    query_text = "Andorra"
    annotator.gazetteer.config.location_coordinates.crs = crs
    candidate_descriptions, existing_candidate_is_appended = (
        annotator.get_candidate_descriptions(toponym, toponym_text, query_text)
    )
    # check return types and contents
    assert type(existing_candidate_is_appended) is bool
    assert type(candidate_descriptions) is list
    for description in candidate_descriptions:
        for key in ["loc_id", "description", "attributes", "latitude", "longitude"]:
            assert key in description.keys()
    # check that the correct loc_id has been returned
    assert candidate_descriptions[0]["loc_id"] == radio_andorra_id
    # check if the candidate has been appended
    if loc_id != "":
        assert existing_candidate_is_appended is True
        assert len(candidate_descriptions) == 2
        assert candidate_descriptions[1]["loc_id"] == loc_id
    else:
        assert len(candidate_descriptions) == 1
    # check return types for coordinates
    lat, long = (
        candidate_descriptions[0]["latitude"],
        candidate_descriptions[0]["longitude"],
    )
    if coordinates is None:
        assert lat is None and long is None
    elif coordinates == 0.0 and crs != "EPSG:2056":
        assert lat == long == 0.0
    elif coordinates == 1 + 9j:
        assert lat is None and long is None


def test_get_filter_attributes(
    annotator: GeoparserAnnotator, geonames_filter_attributes: list[str]
):
    assert annotator.get_filter_attributes() == geonames_filter_attributes


@pytest.mark.parametrize("loc_id", ["", "3039332"])
def test_get_candidates(
    annotator: GeoparserAnnotator, geonames_filter_attributes: list[str], loc_id: str
):
    toponym = {
        "text": "Andorra",
        "start": 0,
        "end": 7,
        "loc_id": loc_id,
    }
    toponym_text = "Andorra"
    query_text = "Andorra"
    result = annotator.get_candidates(toponym, toponym_text, query_text)
    assert type(result) is dict
    candidates = result["candidates"]
    filter_attributes = result["filter_attributes"]
    existing_loc_id = result["existing_loc_id"]
    existing_candidate = result["existing_candidate"]
    if loc_id != "":
        assert len(candidates) == 2
        assert existing_candidate == candidates[-1]
    else:
        assert len(candidates) == 1
        assert existing_candidate is None
    assert filter_attributes == geonames_filter_attributes
    assert existing_loc_id == loc_id


@pytest.mark.parametrize("one_sense_per_discourse", [True, False])
def test_annotate_toponyms(
    annotator: GeoparserAnnotator, radio_andorra_id: str, one_sense_per_discourse: bool
):
    existing_loc_id = "3039332"
    toponyms = [
        {  # toponym to be annotated
            "text": "Andorra",
            "start": 0,
            "end": 7,
            "loc_id": "",
        },
        {  # different toponym (same text) without annotation
            "text": "Andorra",
            "start": 10,
            "end": 17,
            "loc_id": "",
        },
        {  # different toponym (same text) with existing annotation
            "text": "Andorra",
            "start": 20,
            "end": 27,
            "loc_id": existing_loc_id,
        },
    ]
    annotation = {
        "toponym": "Andorra",
        "start": 0,
        "end": 7,
        "loc_id": radio_andorra_id,
    }
    result = annotator.annotate_toponyms(toponyms, annotation, one_sense_per_discourse)
    # annotated toponym is always changed
    assert result[0]["loc_id"] == radio_andorra_id
    # annotation of different toponyms (same text) with existing annotations
    # depends on one sense per discourse
    if one_sense_per_discourse:
        assert result[1]["loc_id"] == radio_andorra_id
    else:
        assert result[1]["loc_id"] == ""
    # different toponyms with existing annotations are never changed
    assert result[2]["loc_id"] == existing_loc_id


def test_remove_toponym(annotator: GeoparserAnnotator, radio_andorra_id: str):
    doc = {
        "filename": "test.txt",
        "spacy_model": "en_core_web_sm",
        "text": "Andorra is a nice place",
        "toponyms": [
            {
                "text": "Andorra",
                "start": 0,
                "end": 7,
                "loc_id": radio_andorra_id,
            }
        ],
    }
    toponym = {
        "text": "Andorra",
        "start": 0,
        "end": 7,
        "loc_id": radio_andorra_id,
    }
    result = annotator.remove_toponym(doc, toponym)
    assert len(result["toponyms"]) == 0
