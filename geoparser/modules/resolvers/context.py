"""
Sizing a reference's context to an encoder's token budget.

An encoder truncates anything past its maximum sequence length, so a resolver
cannot simply hand it a whole document: it has to choose which part of the
text around a reference is worth spending the budget on. That choice is
arithmetic over sentence costs -- which sentence holds the reference, and how
far outwards the window can grow before the budget runs out.

Nothing here knows what produced those costs. A tokenizer, a sentence splitter
and an embedding model all live on the other side of the
:class:`Sentence` value object, which is what lets this logic be exercised
directly rather than through three mocked models. The module imports nothing
from the rest of the package and nothing from the machine learning stack.
"""

from __future__ import annotations

import typing as t
from dataclasses import dataclass

# What the window's sentences are joined with. A single space is what the
# encoder was trained on; anything else shifts the tokenization of every
# sentence boundary in the context.
_JOIN = " "


@dataclass(frozen=True)
class Sentence:
    """
    One sentence of a document, with what it costs to encode it.

    Attributes:
        text: The sentence as it appears in the document
        start: Character offset of the sentence's first character
        end: Character offset just past the sentence's last character
        cost: Tokens the encoder would spend on this sentence
    """

    text: str
    start: int
    end: int
    cost: int

    def covers(self, offset: int) -> bool:
        """
        Whether a character offset falls inside this sentence.

        Args:
            offset: Character offset into the document

        Returns:
            True when the offset lies in this sentence's half-open span
        """
        return self.start <= offset < self.end


def locate_sentence(sentences: t.Sequence[Sentence], start: int, end: int) -> int:
    """
    Find the sentence a reference begins in.

    Args:
        sentences: The document's sentences, in order
        start: Start offset of the reference
        end: End offset of the reference, used only to report a failure

    Returns:
        Index into ``sentences``

    Raises:
        ValueError: If the reference falls in no sentence -- a span past the
            end of the text, or in a gap the splitter left uncovered.
    """
    for index, sentence in enumerate(sentences):
        if sentence.covers(start):
            return index
    raise ValueError(f"No sentence contains reference at position {start}-{end}")


@dataclass(frozen=True)
class _Reach:
    """How far the window currently reaches, and what is left to spend."""

    first: int
    last: int
    remaining: int


def expand_window(
    sentences: t.Sequence[Sentence], target_index: int, budget: int
) -> list[Sentence]:
    """
    Grow a contiguous window around a sentence while the budget allows.

    Each round offers the window one sentence on each side, preceding first,
    and stops as soon as neither fits. Taking one per side per round rather
    than filling one side first keeps the reference near the middle of the
    context, which is where the encoder attends most.

    The target sentence is always included, even when it alone costs more than
    the budget: the encoder will truncate it, but returning nothing would lose
    the reference altogether.

    Args:
        sentences: The document's sentences, in order
        target_index: Index of the sentence holding the reference
        budget: Tokens available for the whole context

    Returns:
        The contiguous run of sentences to use as context, in document order
    """
    reach = _Reach(
        first=target_index,
        last=target_index,
        remaining=budget - sentences[target_index].cost,
    )

    # A round either extends the window or ends it, and the window can extend
    # at most once per sentence, so this bound is never the reason it stops.
    # Stating it makes non-termination impossible rather than merely unlikely.
    for _ in range(len(sentences)):
        grown = _extend_after(sentences, _extend_before(sentences, reach))
        if grown == reach:
            break
        reach = grown

    return list(sentences[reach.first : reach.last + 1])


def _extend_before(sentences: t.Sequence[Sentence], reach: _Reach) -> _Reach:
    """
    Take the preceding sentence, if it exists and still fits.

    Args:
        sentences: The document's sentences, in order
        reach: How far the window reaches now

    Returns:
        The new reach, or the one given when the neighbour does not fit
    """
    cost = _affordable_cost(sentences, reach.first - 1, reach.remaining)
    if cost is None:
        return reach
    return _Reach(reach.first - 1, reach.last, reach.remaining - cost)


def _extend_after(sentences: t.Sequence[Sentence], reach: _Reach) -> _Reach:
    """
    Take the following sentence, if it exists and still fits.

    Args:
        sentences: The document's sentences, in order
        reach: How far the window reaches now

    Returns:
        The new reach, or the one given when the neighbour does not fit
    """
    cost = _affordable_cost(sentences, reach.last + 1, reach.remaining)
    if cost is None:
        return reach
    return _Reach(reach.first, reach.last + 1, reach.remaining - cost)


def select_context(
    sentences: t.Sequence[Sentence], start: int, end: int, budget: int
) -> str:
    """
    The text to encode for one reference.

    Args:
        sentences: The document's sentences, in order
        start: Start offset of the reference
        end: End offset of the reference
        budget: Tokens available for the whole context

    Returns:
        The window's sentences, joined as prose

    Raises:
        ValueError: If the reference falls in no sentence
    """
    target_index = locate_sentence(sentences, start, end)
    window = expand_window(sentences, target_index, budget)
    return _JOIN.join(sentence.text for sentence in window)


def _affordable_cost(
    sentences: t.Sequence[Sentence], index: int, remaining: int
) -> int | None:
    """
    The cost of a neighbouring sentence, if it exists and still fits.

    Args:
        sentences: The document's sentences, in order
        index: Index of the neighbour being considered
        remaining: Tokens left in the budget

    Returns:
        The neighbour's cost, or None when there is no such sentence or it
        would not fit
    """
    if index < 0 or index >= len(sentences):
        return None
    cost = sentences[index].cost
    return cost if cost <= remaining else None
