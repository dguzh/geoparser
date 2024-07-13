import pandas as pd
import pytest


@pytest.fixture
def test_chunk_full() -> pd.DataFrame:
    data = {"col1": [1, 2, 3], "col2": ["a", "b", "c"]}
    return pd.DataFrame.from_dict(data)
