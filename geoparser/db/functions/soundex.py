"""
Soundex phonetic encoding for fuzzy matching candidate retrieval.
"""

# Soundex letter-to-digit mapping. Vowels (and y), as well as h and w, are not
# included and are treated as non-coding letters.
_SOUNDEX_CODES = {
    "B": "1",
    "F": "1",
    "P": "1",
    "V": "1",
    "C": "2",
    "G": "2",
    "J": "2",
    "K": "2",
    "Q": "2",
    "S": "2",
    "X": "2",
    "Z": "2",
    "D": "3",
    "T": "3",
    "L": "4",
    "M": "5",
    "N": "5",
    "R": "6",
}


def soundex(text: str) -> str:
    """
    Compute the American Soundex code for a string.

    The Soundex code is a four-character phonetic hash consisting of the first
    letter followed by three digits. It is used to retrieve candidate names that
    sound alike before final ranking.

    Args:
        text: String to encode. May be None or contain non-alphabetic characters.

    Returns:
        Four-character Soundex code, or an empty string if there are no letters.
    """
    if not text:
        return ""

    letters = [char for char in text.upper() if char.isalpha()]
    if not letters:
        return ""

    first = letters[0]
    result = first
    previous_code = _SOUNDEX_CODES.get(first, "")

    for char in letters[1:]:
        # h and w are transparent: they do not reset adjacency tracking, so two
        # letters with the same code separated by h or w are coded only once.
        if char in ("H", "W"):
            continue

        code = _SOUNDEX_CODES.get(char, "")
        if code and code != previous_code:
            result += code
            if len(result) >= 4:
                break

        # Vowels (code "") reset adjacency, so identical codes separated by a
        # vowel are coded twice.
        previous_code = code

    return (result + "000")[:4]
