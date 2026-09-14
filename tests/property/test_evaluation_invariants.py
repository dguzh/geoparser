import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from geoparser.evaluation import (
    Annotation,
    recognition_f1,
    recognition_precision,
    recognition_recall,
)

pytestmark = pytest.mark.property


@st.composite
def annotation_strategy(draw: st.DrawFn) -> Annotation:
    start = draw(st.integers(min_value=0, max_value=50))
    end = draw(st.integers(min_value=start + 1, max_value=60))
    return Annotation(start, end)


annotation_lists = st.lists(annotation_strategy(), max_size=20)


@settings(max_examples=80, derandomize=True, deadline=None)
@given(expected=annotation_lists, predicted=annotation_lists)
def test_recognition_metrics_are_bounded(
    expected: list[Annotation], predicted: list[Annotation]
) -> None:
    metrics = (
        recognition_precision(expected, predicted),
        recognition_recall(expected, predicted),
        recognition_f1(expected, predicted),
    )

    assert all(0.0 <= metric <= 1.0 for metric in metrics)


@settings(max_examples=80, derandomize=True, deadline=None)
@given(annotations=annotation_lists)
def test_perfect_predictions_have_perfect_f1(annotations: list[Annotation]) -> None:
    assert recognition_f1(annotations, annotations) == 1.0


@settings(max_examples=80, derandomize=True, deadline=None)
@given(annotations=annotation_lists)
def test_duplicate_predictions_do_not_inflate_true_positives(
    annotations: list[Annotation],
) -> None:
    duplicated = annotations + annotations

    assert recognition_precision(annotations, duplicated) == 1.0
    assert recognition_recall(annotations, duplicated) == 1.0


@settings(max_examples=80, derandomize=True, deadline=None)
@given(expected=annotation_lists, predicted=annotation_lists)
def test_swapping_inputs_swaps_precision_and_recall(
    expected: list[Annotation], predicted: list[Annotation]
) -> None:
    assert recognition_precision(expected, predicted) == recognition_recall(
        predicted, expected
    )
    assert recognition_recall(expected, predicted) == recognition_precision(
        predicted, expected
    )


@settings(max_examples=80, derandomize=True, deadline=None)
@given(expected=annotation_lists, predicted=annotation_lists)
def test_f1_lies_between_precision_and_recall(
    expected: list[Annotation], predicted: list[Annotation]
) -> None:
    precision = recognition_precision(expected, predicted)
    recall = recognition_recall(expected, predicted)
    f1 = recognition_f1(expected, predicted)

    lower = min(precision, recall)
    upper = max(precision, recall)
    assert lower - 1e-12 <= f1 <= upper + 1e-12
