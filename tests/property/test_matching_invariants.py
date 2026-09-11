import string

import pytest
from hypothesis import given, strategies as st

from geoparser.db.functions import levenshtein, soundex


ASCII_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + string.punctuation + " \t",
    max_size=80,
)
NO_LETTERS = st.text(
    alphabet=string.digits + string.punctuation + " \t",
    max_size=80,
)


@pytest.mark.property
@given(NO_LETTERS)
def test_soundex_is_empty_when_generated_input_has_no_letters(text: str) -> None:
    assert soundex(text) == ""


@pytest.mark.property
@given(ASCII_TEXT.filter(lambda text: any(char.isalpha() for char in text)))
def test_soundex_has_a_letter_and_three_digits_for_generated_text(text: str) -> None:
    result = soundex(text)

    assert len(result) == 4
    assert result[0].isalpha()
    assert result[1:].isdigit()


@pytest.mark.property
@given(ASCII_TEXT)
def test_soundex_is_case_invariant_for_generated_ascii_text(text: str) -> None:
    assert soundex(text) == soundex(text.swapcase())


@pytest.mark.property
@given(ASCII_TEXT, ASCII_TEXT)
def test_levenshtein_is_symmetric_and_non_negative(
    left: str, right: str
) -> None:
    distance = levenshtein(left, right)

    assert distance >= 0
    assert distance == levenshtein(right, left)


@pytest.mark.property
@given(ASCII_TEXT)
def test_levenshtein_has_zero_distance_for_equivalent_inputs(text: str) -> None:
    assert levenshtein(text, text) == 0
