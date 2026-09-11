"""
Soundex checked against the published reference codes.

The algorithm has two rules that are easy to drop without any obvious effect:
h and w are transparent (two same-coded letters separated by one are coded
once), while a vowel between them resets that adjacency. These cases are the
standard worked examples for exactly those rules.
"""

import pytest

from geoparser.db.functions.soundex import soundex


@pytest.mark.unit
class TestSoundexReferenceCodes:
    """Published American Soundex values."""

    @pytest.mark.parametrize(
        ("name", "code"),
        [
            # h is transparent: the s and the c either side code once.
            ("Ashcraft", "A261"),
            # z and k separated by a vowel are coded twice.
            ("Tymczak", "T522"),
            # A leading silent letter still supplies the initial.
            ("Pfister", "P236"),
            # Different spellings that must collide.
            ("Robert", "R163"),
            ("Rupert", "R163"),
            ("Honeyman", "H555"),
            ("Washington", "W252"),
        ],
    )
    def test_matches_the_published_code(self, name, code):
        """Each reference name encodes to its documented value."""
        assert soundex(name) == code

    def test_treats_w_as_transparent_between_same_coded_letters(self):
        """
        A w between two same-coded consonants does not break adjacency.

        Without the rule the second consonant would be coded again, so this
        distinguishes a correct implementation from one that only special
        cases h.
        """
        # "Bwb": b and b are both code 1, separated only by w
        assert soundex("Bwb") == "B000"

    def test_a_vowel_between_same_coded_letters_does_break_adjacency(self):
        """The contrast case: a vowel resets adjacency, so the code repeats."""
        assert soundex("Bab") == "B100"

    def test_is_case_insensitive(self):
        """Case in the input does not change the code."""
        assert soundex("ashcraft") == soundex("ASHCRAFT") == "A261"

    def test_ignores_non_alphabetic_characters(self):
        """Punctuation and digits are skipped rather than coded."""
        assert soundex("O'Brien-2") == soundex("OBrien")

    @pytest.mark.parametrize("text", ["", "1234", "  "])
    def test_returns_empty_without_letters(self, text):
        """Nothing to encode yields an empty code, not a padded one."""
        assert soundex(text) == ""
