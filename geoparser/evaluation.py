"""Pure evaluation metrics for recognition and resolution pilots."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Annotation:
    """A character span with an optional gazetteer identifier."""

    start: int
    end: int
    identifier: str | None = None

    @property
    def span(self) -> tuple[int, int]:
        """Return the half-open character span."""
        return self.start, self.end


def _unique_spans(annotations: Sequence[Annotation]) -> set[tuple[int, int]]:
    """Return distinct spans, ignoring any resolution identifiers."""
    return {annotation.span for annotation in annotations}


def _resolved_pairs(
    annotations: Sequence[Annotation],
) -> set[tuple[tuple[int, int], str]]:
    """Return distinct spans paired with their available identifiers."""
    return {
        (annotation.span, annotation.identifier)
        for annotation in annotations
        if annotation.identifier is not None
    }


def _ratio(numerator: int, denominator: int) -> float:
    """Return a bounded ratio, treating an empty comparison as perfect."""
    return numerator / denominator if denominator else 1.0


def recognition_precision(
    expected: Sequence[Annotation], predicted: Sequence[Annotation]
) -> float:
    """Measure the fraction of predicted spans that are expected."""
    expected_spans = _unique_spans(expected)
    predicted_spans = _unique_spans(predicted)
    true_positives = len(expected_spans & predicted_spans)
    return _ratio(true_positives, len(predicted_spans))


def recognition_recall(
    expected: Sequence[Annotation], predicted: Sequence[Annotation]
) -> float:
    """Measure the fraction of expected spans that were predicted."""
    expected_spans = _unique_spans(expected)
    predicted_spans = _unique_spans(predicted)
    true_positives = len(expected_spans & predicted_spans)
    return _ratio(true_positives, len(expected_spans))


def recognition_f1(
    expected: Sequence[Annotation], predicted: Sequence[Annotation]
) -> float:
    """Return the harmonic mean of recognition precision and recall."""
    precision = recognition_precision(expected, predicted)
    recall = recognition_recall(expected, predicted)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def resolution_accuracy(
    expected: Sequence[Annotation], predicted: Sequence[Annotation]
) -> float:
    """Measure exact span-and-identifier matches against resolved gold pairs."""
    expected_pairs = _resolved_pairs(expected)
    predicted_pairs = _resolved_pairs(predicted)
    correct = len(expected_pairs & predicted_pairs)
    return _ratio(correct, len(expected_pairs))
