import tempfile
import typing as t
from contextlib import nullcontext
from pathlib import Path

import pytest
from datasets import Dataset

from geoparser import constants as C
from geoparser.geodoc import GeoDoc
from geoparser.trainer import GeoparserTrainer


@pytest.fixture(scope="session")
def corpus_good_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Radio Andorra", 26, 39, 3039328), ("Roc Meler", 0, 9, 2994701)],
        ),
        (
            "Typhoon hit Taiwan today #prayfortaiwan",
            [("taiwan", 33, 39, 3039328), ("Taiwan", 12, 18, 3039328)],
        ),
        (  # includes an annotation that is not a toponym
            "Some End of Sentence|New York!!!",
            [("New York", 21, 29, 3039328), ("Some", 0, 4, 3039328)],
        ),
    ]
    return corpus


@pytest.fixture(scope="session")
def corpus_bad_annotations() -> list[tuple[str, list[tuple[str, int, int, int]]]]:
    corpus = [
        (
            "Roc Meler is mentioned on Radio Andorra.",
            [("Radio Andorra", 23, 39, 3039328), ("Roc Meler", 0, 7, 2994701)],
        ),
        (
            "Typhoon hit Taiwan today #prayfortaiwan",
            [("taiwan", 33, 40, 3039328), ("Taiwan", 11, 18, 3039328)],
        ),
        (  # includes an annotation that is not a toponym
            "Some End of Sentence|New York!!!",
            [("New York", 0, 30, 3039328), ("Some", 0, 3, 3039328)],
        ),
    ]
    return corpus


@pytest.fixture(scope="session")
def geodocs_corpus(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
) -> list[GeoDoc]:
    return [trainer_real_data.nlp(seg[0]) for seg in corpus_good_annotations]


@pytest.fixture(scope="function")
def eval_doc(trainer_real_data: GeoparserTrainer) -> list[GeoDoc]:
    text = "Germany is not Italy"
    return trainer_real_data.nlp(text)


@pytest.fixture(scope="session")
def train_corpus(trainer_real_data: GeoparserTrainer) -> list[GeoDoc]:
    corpus = [
        (
            "Ordino is a town in the mountains.",
            [("Ordino", 0, 6, 3039678)],
        ),
    ]
    return trainer_real_data.annotate(corpus, include_unmatched=True)


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


@pytest.mark.parametrize("include_unmatched", [True, False])
def test_annotate(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[tuple[str, list[tuple[str, int, int, int]]]],
    include_unmatched: bool,
):
    annotated_corpus = trainer_real_data.annotate(
        corpus_good_annotations, include_unmatched=include_unmatched
    )
    assert type(annotated_corpus) is list
    for doc, raw_doc in zip(annotated_corpus, corpus_good_annotations):
        assert type(doc) is GeoDoc
        # entities are sorted by occurrence in text
        assert list(doc.ents) == sorted(doc.ents, key=lambda x: x.start)
        # include all annotations if include_unmatched
        if include_unmatched:
            ents_str = {ent.text for ent in doc.ents}
            for annotation in raw_doc[1]:
                annotation_str = annotation[0]
                assert annotation_str in ents_str
            # retokenization example
            if (taiwan := "taiwan") in raw_doc[0]:
                assert taiwan in ents_str
        # check annotation boundaries
        for doc_ent, raw_ent in zip(doc.ents, sorted(raw_doc[1], key=lambda x: x[1])):
            assert doc[doc_ent.start : doc_ent.end].text == raw_ent[0]


@pytest.mark.parametrize(
    "distances,expected", [([0.0, 0.0], 0.0), ([1.0, 1.0], 0.06997644)]
)
def test_auc(
    trainer_real_data: GeoparserTrainer, distances: list[float], expected: float
):
    assert trainer_real_data.calculate_auc(distances) == pytest.approx(
        expected, rel=1e-5
    )


@pytest.mark.parametrize(
    "predicted_id1,gold_id1,predicted_id2,gold_id2,expected",
    [
        (1, None, 1, None, None),  # all gold_id being None raises ZeroDivisionError
        (1, 2, 1, 2, None),  # invalid gold_id has the same effect
        (  # predicted_id is None
            None,
            1,
            None,
            1,
            {
                "Accuracy": 0.0,
                "Accuracy@161km": 0.0,
                "MeanErrorDistance": C.MAX_ERROR,
                "AreaUnderTheCurve": 1.0,
            },
        ),
        (  # perfect prediction
            1,
            1,
            1,
            1,
            {
                "Accuracy": 1.0,
                "Accuracy@161km": 1.0,
                "MeanErrorDistance": 0.0,
                "AreaUnderTheCurve": 0.0,
            },
        ),
        (  # not perfect, but both in Andorra
            3039328,
            2994701,
            2994701,
            3039328,
            {
                "Accuracy": 0.0,
                "Accuracy@161km": 1.0,
                "MeanErrorDistance": 15.480857,
                "AreaUnderTheCurve": 0.282895,
            },
        ),
    ],
)
def test_evaluate(
    trainer_real_data: GeoparserTrainer,
    eval_doc: list[GeoDoc],
    predicted_id1: int,
    gold_id1: int,
    predicted_id2: int,
    gold_id2: int,
    expected: t.Optional[dict[str, float]],
):
    eval_doc.toponyms[0]._.loc_id, eval_doc.toponyms[0]._.gold_loc_id = (
        predicted_id1,
        gold_id1,
    )
    eval_doc.toponyms[1]._.loc_id, eval_doc.toponyms[1]._.gold_loc_id = (
        predicted_id2,
        gold_id2,
    )
    with (
        pytest.raises(ZeroDivisionError)
        if (gold_id1 is None and gold_id2 is None)
        or 2 == gold_id1 == gold_id2  # 2 is used as an invalid id not in the gazetteer
        else nullcontext()
    ):
        result = trainer_real_data.evaluate([eval_doc])
        for key, result_value in result.items():
            assert result_value == pytest.approx(expected[key], rel=1e-5)


def test_prepare_training_data(
    trainer_real_data: GeoparserTrainer, train_corpus: list[GeoDoc]
):
    prepared = trainer_real_data.prepare_training_data(train_corpus)
    assert type(prepared) is Dataset
    assert (
        len(prepared["toponym_texts"])
        == len(prepared["candidate_texts"])
        == len(prepared["label"])
    )
    for text, candidate_text, label in zip(
        prepared["toponym_texts"], prepared["candidate_texts"], prepared["label"]
    ):
        assert text == train_corpus[0].text
        candidates_labels = {
            "Ordino (first-order administrative division) in Ordino, Andorra": 0,
            "Ordino (seat of a first-order administrative division) in Ordino, Andorra": 1,
        }
        assert candidates_labels[candidate_text] == label


def test_train(trainer_real_data: GeoparserTrainer, train_corpus: list[GeoDoc]):
    output_dir = tempfile.mkdtemp()
    # test if training runs without errors for a single epoch
    trainer_real_data.train(train_corpus, epochs=1, output_path=output_dir)
    # output path must not be empty
    contents = Path(output_dir).iterdir()
    assert next(contents, None) is not None
