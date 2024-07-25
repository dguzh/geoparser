import pytest

from geoparser.geodoc import GeoDoc
from geoparser.trainer import GeoparserTrainer


@pytest.fixture(scope="session")
def corpus_good_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Roc Meler", 0, 9, 2994701), ("Radio Andorra", 26, 39, 3039328)],
        )
    ]
    return corpus


@pytest.fixture(scope="session")
def corpus_bad_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Roc Meler", 0, 7, 2994701), ("Radio Andorra", 23, 39, 3039328)],
        )
    ]
    return corpus


@pytest.fixture(scope="session")
def geodocs_corpus(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
) -> list[GeoDoc]:
    return [trainer_real_data.nlp(corpus_good_annotations[0][0])]


def test_find_toponym(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    corpus_bad_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    geodocs_corpus: list[GeoDoc],
):
    for good_segment, bad_segment in zip(
        corpus_good_annotations, corpus_bad_annotations
    ):
        for good_annot, bad_annot in zip(
            [annot for annot in good_segment[1]], [annot for annot in bad_segment[1]]
        ):
            good_start, good_end = good_annot[1], good_annot[2]
            bad_start, bad_end = bad_annot[1], bad_annot[2]
            toponym = good_annot[0]
            assert trainer_real_data.find_toponym(
                toponym, geodocs_corpus[0], bad_start, bad_end
            ) == (good_start, good_end)
