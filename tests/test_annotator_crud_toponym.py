import typing as t
import uuid
from contextlib import nullcontext

import pytest
from sqlmodel import Session as DBSession

from geoparser import Geoparser
from geoparser.annotator.db.crud import (
    DocumentRepository,
    SessionRepository,
    SessionSettingsRepository,
    ToponymRepository,
)
from geoparser.annotator.db.models import (
    Document,
    DocumentCreate,
    SessionCreate,
    SessionSettingsUpdate,
    Toponym,
    ToponymBase,
    ToponymCreate,
    ToponymUpdate,
)
from geoparser.annotator.exceptions import (
    ToponymNotFoundException,
    ToponymOverlapException,
)
from geoparser.annotator.models.api import CandidatesGet
from geoparser.gazetteers import GeoNames


@pytest.fixture(scope="session")
def geonames_filter_attributes() -> list[str]:
    return [
        "name",
        "feature_type",
        "admin2_name",
        "admin1_name",
        "country_name",
    ]


@pytest.mark.parametrize(
    "existing_start, existing_end, new_start, new_end, should_raise",
    [
        (0, 4, 5, 10, False),  # No overlap (existing before new)
        (11, 15, 5, 10, False),  # No overlap (existing after new)
        (5, 10, 5, 10, True),  # Exact overlap
        (
            5,
            10,
            8,
            12,
            True,
        ),  # Partial overlap (existing starts before, ends within new)
        (
            8,
            12,
            5,
            10,
            True,
        ),  # Partial overlap (existing starts within new, ends after)
    ],
)
def test_validate_overlap(
    test_db: DBSession,
    existing_start: int,
    existing_end: int,
    new_start: int,
    new_end: int,
    should_raise: bool,
):
    document_id = uuid.uuid4()
    # Create and insert the existing toponym
    existing_toponym = ToponymCreate(
        text="Existing", start=existing_start, end=existing_end, document_id=document_id
    )
    ToponymRepository.create(
        test_db, existing_toponym, additional={"document_id": document_id}
    )
    # Define the new toponym
    new_toponym = ToponymCreate(
        text="New", start=new_start, end=new_end, document_id=document_id
    )
    with nullcontext() if not should_raise else pytest.raises(ToponymOverlapException):
        created_toponym = ToponymRepository.create(
            test_db, new_toponym, additional={"document_id": document_id}
        )
        assert created_toponym.text == "New"
        assert created_toponym.start == new_start
        assert created_toponym.end == new_end


@pytest.mark.parametrize(
    "old_toponyms, new_toponyms, expected_remaining",
    [
        # No duplicates → All new toponyms are kept
        (
            [],
            [ToponymCreate(text="Paris", start=0, end=5)],
            [ToponymCreate(text="Paris", start=0, end=5)],
        ),
        # New toponym overlaps with an existing one → It is removed
        (
            [ToponymCreate(text="Paris", start=0, end=5)],
            [ToponymCreate(text="Paris", start=0, end=5)],
            [],
        ),
        # Mixed case: One duplicate, one unique → Only unique one remains
        (
            [ToponymCreate(text="Paris", start=0, end=5)],
            [
                ToponymCreate(text="Paris", start=0, end=5),
                ToponymCreate(text="Berlin", start=10, end=15),
            ],
            [ToponymCreate(text="Berlin", start=10, end=15)],
        ),
        # Same text, different positions → They are treated as unique
        (
            [ToponymCreate(text="Paris", start=0, end=5)],
            [ToponymCreate(text="Paris", start=10, end=15)],
            [ToponymCreate(text="Paris", start=10, end=15)],
        ),
    ],
)
def test_remove_duplicates(
    old_toponyms: list[ToponymCreate],
    new_toponyms: list[ToponymCreate],
    expected_remaining: list[ToponymCreate],
):
    filtered_toponyms = ToponymRepository._remove_duplicates(old_toponyms, new_toponyms)
    assert len(filtered_toponyms) == len(expected_remaining)
    for expected in expected_remaining:
        assert any(
            t.text == expected.text
            and t.start == expected.start
            and t.end == expected.end
            for t in filtered_toponyms
        )


@pytest.mark.parametrize("loc_id", ["", "3039332"])
@pytest.mark.parametrize("crs", ["EPSG:4326", "EPSG:2056"])
@pytest.mark.parametrize("coordinates", [None, 0.0, 1 + 9j])
def test_get_candidate_descriptions(
    geoparser_real_data: Geoparser,
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
    toponym = ToponymCreate(
        text="Andorra",
        start=0,
        end=7,
        loc_id=loc_id,
    )
    toponym_text = "Andorra"
    query_text = "Andorra"
    geoparser_real_data.gazetteer.config.location_coordinates.crs = crs
    candidate_descriptions, existing_candidate_is_appended = (
        ToponymRepository.get_candidate_descriptions(
            geoparser_real_data, toponym, toponym_text, query_text
        )
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


def test_create(test_db: DBSession):
    document_id = uuid.uuid4()
    toponym_data = ToponymCreate(text="Paris", start=0, end=5)

    created_toponym = ToponymRepository.create(
        test_db, toponym_data, additional={"document_id": document_id}
    )

    assert created_toponym.id is not None
    assert created_toponym.text == "Paris"
    assert created_toponym.start == 0
    assert created_toponym.end == 5
    assert created_toponym.document_id == document_id


def test_create_overlap(test_db: DBSession):
    document_id = uuid.uuid4()
    toponym1 = ToponymCreate(text="London", start=5, end=10, document_id=document_id)
    ToponymRepository.create(test_db, toponym1, additional={"document_id": document_id})
    toponym2 = ToponymCreate(text="New York", start=8, end=15, document_id=document_id)
    with pytest.raises(ToponymOverlapException):
        ToponymRepository.create(
            test_db, toponym2, additional={"document_id": document_id}
        )


@pytest.mark.parametrize("valid_id", [True, False])
def test_read(test_db: DBSession, test_toponym: Toponym, valid_id: bool):
    fetch_id = test_toponym.id if valid_id else uuid.uuid4()
    with nullcontext() if valid_id else pytest.raises(ToponymNotFoundException):
        fetched_toponym = ToponymRepository.read(test_db, fetch_id)
        print(fetched_toponym)
        assert fetched_toponym.model_dump() == test_toponym.model_dump()


@pytest.mark.parametrize(
    "toponyms, search_start, search_end, expected_text",
    [
        ([ToponymCreate(text="Paris", start=0, end=5)], 0, 5, "Paris"),  # Exact match
        ([ToponymCreate(text="Berlin", start=10, end=15)], 0, 5, None),  # No match
        (
            [
                ToponymCreate(text="Rome", start=7, end=12),
                ToponymCreate(text="Madrid", start=0, end=5),
            ],
            7,
            12,
            "Rome",
        ),  # Finds correct toponym
    ],
)
def test_get_toponym_private(toponyms, search_start, search_end, expected_text):
    result = ToponymRepository._get_toponym(toponyms, search_start, search_end)
    assert (result.text if result else None) == expected_text


@pytest.mark.parametrize(
    "toponyms, search_start, search_end, expected_text",
    [
        (  # Case 1: Matching toponym found
            [
                Toponym(text="Paris", start=0, end=5, document_id=uuid.uuid4()),
                Toponym(text="Berlin", start=10, end=15, document_id=uuid.uuid4()),
            ],
            10,
            15,
            "Berlin",
        ),
        (  # Case 2: No matching toponym
            [Toponym(text="Rome", start=7, end=12, document_id=uuid.uuid4())],
            0,
            5,
            None,
        ),
    ],
)
def test_get_toponym(toponyms, search_start, search_end, expected_text):
    doc = Document(id=uuid.uuid4(), text="Sample text", toponyms=toponyms)

    result = ToponymRepository.get_toponym(doc, search_start, search_end)

    assert (result.text if result else None) == expected_text


def test_read_all(test_db: DBSession):
    document_id = uuid.uuid4()
    toponym1 = ToponymRepository.create(
        test_db,
        ToponymCreate(text="Tokyo", start=0, end=5),
        additional={"document_id": document_id},
    )
    toponym2 = ToponymRepository.create(
        test_db,
        ToponymCreate(text="Osaka", start=6, end=11),
        additional={"document_id": document_id},
    )
    # test unfiltered read_all
    all_toponyms = ToponymRepository.read_all(test_db)
    assert [toponym.model_dump() for toponym in all_toponyms] == [
        toponym.model_dump() for toponym in [toponym1, toponym2]
    ]
    # filter by Toponym.id
    filtered_toponyms = ToponymRepository.read_all(test_db, id=toponym2.id)
    assert len(filtered_toponyms) == 1
    assert filtered_toponyms[0].model_dump() == toponym2.model_dump()


@pytest.mark.parametrize("loc_id", ["", "3039332"])
@pytest.mark.parametrize("valid_toponym", [True, False])
def test_get_candidates(
    test_db: DBSession,
    geoparser_real_data: Geoparser,
    geonames_filter_attributes: list[str],
    loc_id: str,
    valid_toponym: bool,
):
    document = DocumentRepository.create(
        test_db,
        DocumentCreate(
            filename="test.txt",
            spacy_model="en_core_web_sm",
            text="Andorra is nice.",
            toponyms=[ToponymCreate(text="Andorra", start=0, end=7, loc_id=loc_id)],
        ),
        additional={"session_id": uuid.uuid4()},
    )
    candidates_get = CandidatesGet(
        text="Andorra",
        query_text="Andorra",
        start=0 if valid_toponym else 99,
        end=7 if valid_toponym else 99,
    )
    with nullcontext() if valid_toponym else pytest.raises(ToponymNotFoundException):
        result = ToponymRepository.get_candidates(
            document, geoparser_real_data, candidates_get
        )
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


def test_update(test_db: DBSession, test_toponym: Toponym):
    update_data = ToponymUpdate(
        id=test_toponym.id,
        text="Barcelona",
        start=0,
        end=9,
        document_id=test_toponym.document_id,
    )
    ToponymRepository.update(test_db, update_data)
    db_toponym = ToponymRepository.read(test_db, test_toponym.id)
    assert db_toponym.model_dump() == update_data.model_dump()


def test_update_overlap(test_db: DBSession):
    document_id = uuid.uuid4()
    toponym1 = ToponymCreate(text="Rome", start=0, end=5)
    created_toponym1 = ToponymRepository.create(
        test_db, toponym1, additional={"document_id": document_id}
    )
    toponym2 = ToponymCreate(text="Venice", start=6, end=10)
    created_toponym2 = ToponymRepository.create(
        test_db, toponym2, additional={"document_id": document_id}
    )
    update_data = ToponymUpdate(
        id=created_toponym2.id, text="Florence", start=3, end=8, document_id=document_id
    )
    with pytest.raises(ToponymOverlapException):
        ToponymRepository.update(test_db, update_data)


@pytest.mark.parametrize(
    "one_sense_per_discourse, expected_loc_id",
    [
        (True, "123"),  # All unannotated occurrences of the same text should get 123
        (False, ""),  # Only the annotated toponym gets updated
    ],
)
def test_annotate_many(
    test_db: DBSession,
    one_sense_per_discourse: bool,
    expected_loc_id: str,
):
    session_create = SessionCreate(
        gazetteer="geonames",
        documents=[
            DocumentCreate(
                filename="test.txt",
                text="Sample text",
                spacy_model="en_core_web_sm",
                toponyms=[
                    ToponymCreate(
                        text="Paris",
                        start=0,
                        end=5,
                    ),
                    ToponymCreate(
                        text="Paris",
                        start=10,
                        end=15,
                    ),
                    ToponymCreate(
                        text="Berlin",
                        start=20,
                        end=25,
                    ),
                ],
            )
        ],
    )
    session = SessionRepository.create(test_db, session_create)
    SessionSettingsRepository.update(
        test_db,
        SessionSettingsUpdate(
            id=session.settings.id, one_sense_per_discourse=one_sense_per_discourse
        ),
    )
    annotation = ToponymBase(text="Paris", start=0, end=5, loc_id="123")
    updated_toponyms = ToponymRepository.annotate_many(
        test_db, session.documents[0], annotation
    )
    assert any(t.loc_id == "123" for t in updated_toponyms if t.text == "Paris")
    assert all(
        t.loc_id == expected_loc_id or t.loc_id == "123"
        for t in updated_toponyms
        if t.text == "Paris"
    )
    assert next(t for t in updated_toponyms if t.text == "Berlin").loc_id == ""


def test_delete(test_db: DBSession):
    document_id = uuid.uuid4()
    toponym_data = ToponymCreate(text="Athens", start=0, end=6)
    created_toponym = ToponymRepository.create(
        test_db, toponym_data, additional={"document_id": document_id}
    )

    deleted_toponym = ToponymRepository.delete(test_db, created_toponym.id)

    assert deleted_toponym.id == created_toponym.id

    with pytest.raises(ToponymNotFoundException):
        ToponymRepository.read(test_db, created_toponym.id)
