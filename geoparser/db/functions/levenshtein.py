"""
Levenshtein edit distance for fuzzy matching ranking.
"""

from rapidfuzz import utils
from rapidfuzz.distance import Levenshtein


def levenshtein(query: str, candidate: str) -> int:
    """
    Compute the Levenshtein edit distance between two strings using rapidfuzz.

    The distance counts the minimum number of single-character insertions,
    deletions, and substitutions required to turn one string into the other.
    Lower values indicate better matches, which matches the ascending-order
    ranking used for fuzzy search. Comparison is case-insensitive and ignores
    non-alphanumeric characters.

    Args:
        query: Search string. May be None.
        candidate: Candidate string to compare against. May be None.

    Returns:
        Non-negative edit distance, where 0 is an exact match.
    """
    return Levenshtein.distance(
        query or "", candidate or "", processor=utils.default_process
    )
