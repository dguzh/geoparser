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


@pytest.mark.parametrize(
    "text,annotated_span",
    [
        ("Typhoon hit Taiwan today #prayfortaiwan", (33, 39)),
        ("Some End of Sentence|New York!!!", (21, 29)),
    ],
)
def test_retokenize_toponym(
    trainer_real_data: GeoparserTrainer, text: str, annotated_span: tuple[int, int]
):
    doc = trainer_real_data.nlp(text)
    annotated_toponym = doc.text[slice(*annotated_span)]
    len_before = len(doc)
    # no span can be created because annotation is not at token boundaries
    assert doc.char_span(*annotated_span) is None
    # annotated toponym (or parts of it if whitespace-delimited) is not a token
    assert not all(
        toponym in [token.text for token in doc]
        for toponym in annotated_toponym.split()
    )
    trainer_real_data.retokenize_toponym(doc, *annotated_span)
    len_after = len(doc)
    span = doc.char_span(*annotated_span)
    # after retokenization, we can create a span and we have more tokens than before
    assert span is not None
    assert span.text == annotated_toponym
    assert len_before < len_after
    # annotated toponym (or parts of it if whitespace-delimited) are tokens
    for toponym in annotated_toponym.split():
        assert toponym in [token.text for token in doc]


def test_retokenize_toponym_do_nothing(trainer_real_data: GeoparserTrainer):
    """
    method has no side-effects on good segments
    """
    text = "Typhoon hit Taiwan today"
    doc = trainer_real_data.nlp(text)
    annotated_span = (12, 18)
    annotated_toponym = doc.text[slice(*annotated_span)]
    len_before = len(doc)
    tokens_before = [token.text for token in doc]
    span = doc.char_span(*annotated_span)
    # span can be found before
    assert span is not None
    assert span.text == annotated_toponym
    trainer_real_data.retokenize_toponym(doc, *annotated_span)
    len_after = len(doc)
    tokens_after = [token.text for token in doc]
    span = doc.char_span(*annotated_span)
    # same span can be found after
    assert span is not None
    assert span.text == annotated_toponym
    # number and text of tokens is still the same
    assert len_before == len_after
    assert tokens_before == tokens_after
