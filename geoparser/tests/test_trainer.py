import pytest

from geoparser.geodoc import GeoDoc
from geoparser.trainer import GeoparserTrainer


@pytest.fixture(scope="session")
def corpus_good_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Roc Meler", 0, 9, 2994701), ("Radio Andorra", 26, 39, 3039328)],
        ),
        (
            "Typhoon hit Taiwan today #prayfortaiwan",
            [("Taiwan", 12, 18, 3039328), ("taiwan", 33, 39, 3039328)],
        ),
        ("Some End of Sentence|New York!!!", [("New York", 21, 29, 3039328)]),
    ]
    return corpus


@pytest.fixture(scope="session")
def corpus_bad_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Roc Meler", 0, 7, 2994701), ("Radio Andorra", 23, 39, 3039328)],
        ),
        (
            "Typhoon hit Taiwan today #prayfortaiwan",
            [("Taiwan", 11, 18, 3039328), ("taiwan", 33, 40, 3039328)],
        ),
        ("Some End of Sentence|New York!!!", [("New York", 0, 30, 3039328)]),
    ]
    return corpus


@pytest.fixture(scope="session")
def geodocs_corpus(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
) -> list[GeoDoc]:
    return [trainer_real_data.nlp(seg[0]) for seg in corpus_good_annotations]


def test_find_toponym(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    corpus_bad_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    geodocs_corpus: list[GeoDoc],
):
    for i, (good_segment, bad_segment) in enumerate(
        zip(corpus_good_annotations, corpus_bad_annotations)
    ):
        for good_annot, bad_annot in zip(
            [annot for annot in good_segment[1]], [annot for annot in bad_segment[1]]
        ):
            good_start, good_end = good_annot[1], good_annot[2]
            bad_start, bad_end = bad_annot[1], bad_annot[2]
            toponym = good_annot[0]
            assert trainer_real_data.find_toponym(
                toponym, geodocs_corpus[i], bad_start, bad_end
            ) == (good_start, good_end)


def test_retokenize_toponym(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    geodocs_corpus: list[GeoDoc],
):
    for segment, doc in zip(corpus_good_annotations, geodocs_corpus):
        for toponym in segment[1]:
            annotated_span = toponym[1:3]
            annotated_toponym = doc.text[slice(*annotated_span)]
            len_before = len(doc)
            tokens_before = [token.text for token in doc]
            span = doc.char_span(*annotated_span)
            # for good segments, the method must not have any side-effects
            good_segment = span is not None
            # in good segments, we can find the span from the beginning
            if good_segment:
                assert span.text == annotated_toponym
            # in bad segments, the annotated toponym (or parts of it if whitespace-delimited)
            # is not a token
            else:
                assert not all(
                    toponym in [token.text for token in doc]
                    for toponym in annotated_toponym.split()
                )
            trainer_real_data.retokenize_toponym(doc, *annotated_span)
            len_after = len(doc)
            tokens_after = [token.text for token in doc]
            span = doc.char_span(*annotated_span)
            assert span.text == annotated_toponym
            # number and text of tokens is still the same
            if good_segment:
                assert len_before == len_after
                assert tokens_before == tokens_after
            # we have more tokens overall and the annotated toponym
            # (or parts of it if whitespace-delimited) is a token
            else:
                assert len_before < len_after
                for toponym in annotated_toponym.split():
                    assert toponym in [token.text for token in doc]
