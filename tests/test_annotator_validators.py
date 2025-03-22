import pytest

from geoparser.annotator.db.models.validators import normalize_newlines


@pytest.mark.parametrize(
    "test_str,expected",
    [
        ("1\n2\n3\n4", "1\n2\n3\n4"),  # leave as is
        ("1\r2\r3\r4", "1\n2\n3\n4"),  # normalize carriage return
        ("1\r\n2\r\n3\r\n4", "1\n2\n3\n4"),  # normalize Windows newlines
        ("1\n2\r3\n4", "1\n2\n3\n4"),  # handle mixed cases
    ],
)
def test_normalize_newlines(test_str: str, expected: str):
    assert normalize_newlines(test_str) == expected
