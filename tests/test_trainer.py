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
def corpus_good_annotations() -> list[dict]:
    corpus = [
        {
            "text": "Roc Meler is mentioned on Radio Andorra.",
            "toponyms": [
                {"text": "Radio Andorra", "start": 26, "end": 39, "loc_id": "3039328"},
                {"text": "Roc Meler", "start": 0, "end": 9, "loc_id": "2994701"},
            ],
        },
        {
            "text": "Typhoon hit Taiwan today #prayfortaiwan",
            "toponyms": [
                {"text": "taiwan", "start": 33, "end": 39, "loc_id": "3039328"},
                {"text": "Taiwan", "start": 12, "end": 18, "loc_id": "3039328"},
            ],
        },
        {
            "text": "Some End of Sentence|New York!!!",
            "toponyms": [  # includes an annotation that is not a toponym
                {"text": "New York", "start": 21, "end": 29, "loc_id": "3039328"},
                {"text": "Some", "start": 0, "end": 4, "loc_id": "3039328"},
            ],
        },
    ]
    return corpus


@pytest.fixture(scope="session")
def corpus_bad_annotations() -> list[dict]:
    corpus = [
        {
            "text": "Roc Meler is mentioned on Radio Andorra.",
            "toponyms": [
                {"text": "Radio Andorra", "start": 23, "end": 39, "loc_id": "3039328"},
                {"text": "Roc Meler", "start": 0, "end": 7, "loc_id": "2994701"},
            ],
        },
        {
            "text": "Typhoon hit Taiwan today #prayfortaiwan",
            "toponyms": [
                {"text": "taiwan", "start": 31, "end": 45, "loc_id": "3039328"},
                {"text": "Taiwan", "start": 11, "end": 18, "loc_id": "3039328"},
            ],
        },
        {
            "text": "Some End of Sentence|New York!!!",
            "toponyms": [  # includes an annotation that is not a toponym
                {"text": "New York", "start": 10, "end": 30, "loc_id": "3039328"},
                {"text": "Some", "start": 1, "end": 3, "loc_id": "3039328"},
            ],
        },
    ]
    return corpus


@pytest.fixture(scope="session")
def geodocs_corpus(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[dict],
) -> list[GeoDoc]:
    return [
        trainer_real_data.nlp(document["text"]) for document in corpus_good_annotations
    ]


@pytest.fixture(scope="function")
def eval_doc(trainer_real_data: GeoparserTrainer) -> list[GeoDoc]:
    text = "Germany is not Italy"
    return trainer_real_data.nlp(text)


@pytest.fixture(scope="session")
def train_corpus(trainer_real_data: GeoparserTrainer) -> list[GeoDoc]:
    corpus = [
        {
            "text": "Ordino is a town in the mountains.",
            "toponyms": [{"text": "Ordino", "start": 0, "end": 6, "loc_id": "3039678"}],
        }
    ]
    return trainer_real_data.annotate(corpus, include_unmatched=True)


def test_find_toponym(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[dict],
    corpus_bad_annotations: list[dict],
    geodocs_corpus: list[GeoDoc],
):
    for i, (good_segment, bad_segment) in enumerate(
        zip(corpus_good_annotations, corpus_bad_annotations)
    ):
        for good_annot, bad_annot in zip(
            good_segment["toponyms"], bad_segment["toponyms"]
        ):
            good_start, good_end = good_annot["start"], good_annot["end"]
            bad_start, bad_end = bad_annot["start"], bad_annot["end"]
            toponym = good_annot["text"]
            assert trainer_real_data._find_toponym(
                toponym, geodocs_corpus[i], bad_start, bad_end
            ) == (good_start, good_end)


def test_retokenize_toponym(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[dict],
    geodocs_corpus: list[GeoDoc],
):
    for segment, doc in zip(corpus_good_annotations, geodocs_corpus):
        for toponym in segment["toponyms"]:
            annotated_span = toponym["start"], toponym["end"]
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
                    t in [token.text for token in doc]
                    for t in annotated_toponym.split()
                )
            trainer_real_data._retokenize_toponym(doc, *annotated_span)
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
                for t in annotated_toponym.split():
                    assert t in [token.text for token in doc]


@pytest.mark.parametrize("include_unmatched", [True, False])
def test_annotate(
    trainer_real_data: GeoparserTrainer,
    corpus_good_annotations: list[dict],
    corpus_bad_annotations: list[dict],
    include_unmatched: bool,
):
    for corpus in [corpus_good_annotations, corpus_bad_annotations]:
        annotated_corpus = trainer_real_data.annotate(
            corpus, include_unmatched=include_unmatched
        )
        assert type(annotated_corpus) is list
        for doc, raw_doc in zip(annotated_corpus, corpus):
            assert type(doc) is GeoDoc
            # entities are sorted by occurrence in text
            assert list(doc.ents) == sorted(doc.ents, key=lambda x: x.start)
            # include all annotations if include_unmatched
            if include_unmatched:
                ents_str = {ent.text for ent in doc.ents}
                for annotation in raw_doc["toponyms"]:
                    annotation_str = annotation["text"]
                    assert annotation_str in ents_str
                if (taiwan := "taiwan") in raw_doc["text"]:
                    assert taiwan in ents_str
            for doc_ent, raw_ent in zip(
                doc.ents, sorted(raw_doc["toponyms"], key=lambda x: x["start"])
            ):
                assert doc[doc_ent.start : doc_ent.end].text == raw_ent["text"]


@pytest.mark.parametrize(
    "distances,expected", [([0.0, 0.0], 0.0), ([1.0, 1.0], 0.06997644)]
)
def test_auc(
    trainer_real_data: GeoparserTrainer, distances: list[float], expected: float
):
    assert trainer_real_data._calculate_auc(distances) == pytest.approx(
        expected, rel=1e-5
    )


@pytest.mark.parametrize(
    "predicted_id1,gold_id1,predicted_id2,gold_id2,expected",
    [
        ("1", None, "1", None, None),  # all gold_id being None raises ZeroDivisionError
        ("1", "2", "1", "2", None),  # invalid gold_id has the same effect
        (  # predicted_id is None
            None,
            "1",
            None,
            "1",
            {
                "Accuracy": 0.0,
                "Accuracy@161km": 0.0,
                "MeanErrorDistance": C.MAX_ERROR,
                "AreaUnderTheCurve": 1.0,
            },
        ),
        (  # perfect prediction
            "1",
            "1",
            "1",
            "1",
            {
                "Accuracy": 1.0,
                "Accuracy@161km": 1.0,
                "MeanErrorDistance": 0.0,
                "AreaUnderTheCurve": 0.0,
            },
        ),
        (  # not perfect, but both in Andorra
            "3039328",
            "2994701",
            "2994701",
            "3039328",
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
    predicted_id1: str,
    gold_id1: str,
    predicted_id2: str,
    gold_id2: str,
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
        or "2"
        == gold_id1
        == gold_id2  # 2 is used as an invalid id not in the gazetteer
        else nullcontext()
    ):
        result = trainer_real_data.evaluate([eval_doc])
        for key, result_value in result.items():
            assert result_value == pytest.approx(expected[key], rel=1e-5)


def test_prepare_training_data(
    trainer_real_data: GeoparserTrainer, train_corpus: list[GeoDoc]
):
    prepared = trainer_real_data._prepare_training_data(train_corpus)
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
            "Ordino (first-order administrative division) in Andorra": 0,
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
