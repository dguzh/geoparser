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


def _starts_new_group(code: str, previous_code: str) -> bool:
    """
    Whether a letter's code opens a new group rather than repeating one.

    Args:
        code: The Soundex digit for this letter, or "" for a non-coding letter
        previous_code: The digit carried over from the preceding letter

    Returns:
        True when the digit should be emitted
    """
    return bool(code) and code != previous_code


def _encode_suffix(letters: list[str], previous_code: str) -> str:
    """
    Encode the letters after the first into at most three digits.

    Args:
        letters: The remaining letters, uppercased
        previous_code: The first letter's code, for adjacency tracking

    Returns:
        Between zero and three Soundex digits
    """
    digits = ""
    for char in letters:
        # h and w are transparent: they do not reset adjacency tracking, so two
        # letters with the same code separated by h or w are coded only once.
        if char in ("H", "W"):
            continue

        # The default only ever reaches _starts_new_group, which asks whether
        # it is truthy, and the adjacency comparison below, where "" and None
        # behave alike: substituting None leaves every code unchanged.
        code = _SOUNDEX_CODES.get(char, "")  # pragma: no mutate
        if _starts_new_group(code, previous_code):
            digits += code

        # Vowels (code "") reset adjacency, so identical codes separated by a
        # vowel are coded twice.
        previous_code = code
        # Stopping later cannot change the result: soundex() truncates to four
        # characters, so a fourth digit is discarded either way.
        if len(digits) >= 3:  # pragma: no mutate
            break
    return digits


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
    # As in _encode_suffix, the default only feeds an adjacency comparison
    # where "" and None behave alike.
    suffix = _encode_suffix(
        letters[1:], _SOUNDEX_CODES.get(first, "")
    )  # pragma: no mutate
    return (first + suffix + "000")[:4]
