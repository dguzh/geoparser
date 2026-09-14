from dataclasses import FrozenInstanceError

import pytest

from geoparser.evaluation import (
    Annotation,
    recognition_f1,
    recognition_precision,
    recognition_recall,
    resolution_accuracy,
)


def test_annotation_is_an_immutable_value_object() -> None:
    annotation = Annotation(2, 8, "3041563")

    assert annotation == Annotation(2, 8, "3041563")
    assert annotation.span == (2, 8)
    with pytest.raises(FrozenInstanceError):
        annotation.start = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    ("expected", "predicted", "precision", "recall", "f1"),
    [
        ([], [], 1.0, 1.0, 1.0),
        ([], [Annotation(0, 4)], 0.0, 1.0, 0.0),
        ([Annotation(0, 4)], [], 1.0, 0.0, 0.0),
        (
            [Annotation(0, 4), Annotation(10, 14)],
            [Annotation(0, 4), Annotation(20, 24)],
            0.5,
            0.5,
            0.5,
        ),
    ],
)
def test_recognition_metrics_cover_empty_and_partial_predictions(
    expected: list[Annotation],
    predicted: list[Annotation],
    precision: float,
    recall: float,
    f1: float,
) -> None:
    assert recognition_precision(expected, predicted) == precision
    assert recognition_recall(expected, predicted) == recall
    assert recognition_f1(expected, predicted) == f1


def test_precision_deduplicates_predicted_spans() -> None:
    expected = [Annotation(0, 4)]
    predicted = [Annotation(0, 4), Annotation(0, 4), Annotation(9, 13)]

    assert recognition_precision(expected, predicted) == 0.5


def test_recall_deduplicates_expected_spans() -> None:
    expected = [Annotation(0, 4), Annotation(0, 4), Annotation(9, 13)]
    predicted = [Annotation(0, 4)]

    assert recognition_recall(expected, predicted) == 0.5


def test_f1_is_zero_when_nonempty_inputs_have_no_overlap() -> None:
    expected = [Annotation(0, 4)]
    predicted = [Annotation(9, 13)]

    assert recognition_f1(expected, predicted) == 0.0


def test_recognition_ignores_identifiers() -> None:
    expected = [Annotation(0, 4, "expected")]
    predicted = [Annotation(0, 4, "predicted")]

    assert recognition_precision(expected, predicted) == 1.0
    assert recognition_recall(expected, predicted) == 1.0


def test_resolution_accuracy_requires_the_expected_identifier() -> None:
    expected = [Annotation(0, 16, "3041563")]

    assert resolution_accuracy(expected, [Annotation(0, 16, "3041563")]) == 1.0
    assert resolution_accuracy(expected, [Annotation(0, 16, "3041564")]) == 0.0
    assert resolution_accuracy(expected, [Annotation(0, 16)]) == 0.0


def test_resolution_accuracy_counts_each_gold_pair_once() -> None:
    expected = [Annotation(0, 16, "3041563")]
    predicted = [
        Annotation(0, 16, "3041563"),
        Annotation(0, 16, "3041563"),
        Annotation(30, 36, "9999999"),
    ]

    assert resolution_accuracy(expected, predicted) == 1.0


def test_resolution_accuracy_is_one_without_resolvable_gold_annotations() -> None:
    assert resolution_accuracy([], [Annotation(0, 4, "3041563")]) == 1.0
