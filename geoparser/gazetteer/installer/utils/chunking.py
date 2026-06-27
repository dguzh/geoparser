from typing import Iterator, Tuple

import sqlalchemy as sa

CHUNKSIZE = 100_000


def count_rows(connection: sa.engine.Connection, table_name: str) -> int:
    """
    Count the rows of a freshly populated source table.

    The installer creates each source table from scratch and only appends
    rows, so rowids are contiguous starting at 1. The maximum rowid therefore
    equals the row count and also bounds the rowid ranges used for chunking.

    Args:
        connection: Database connection
        table_name: Name of the table to count

    Returns:
        Number of rows in the table (0 if empty)
    """
    result = connection.execute(sa.text(f"SELECT MAX(rowid) FROM {table_name}"))
    max_rowid = result.scalar()
    return max_rowid or 0


def iter_rowid_ranges(total_rows: int, chunksize: int) -> Iterator[Tuple[int, int]]:
    """
    Yield inclusive ``(start, end)`` rowid bounds covering all rows in chunks.

    Splits the rowid space of a freshly populated table into consecutive,
    non-overlapping ranges of at most ``chunksize`` rows. This lets large SQL
    operations run in bounded batches instead of a single monolithic statement.

    Args:
        total_rows: Total number of rows (the maximum rowid)
        chunksize: Maximum number of rows per chunk

    Yields:
        Inclusive ``(start, end)`` rowid bounds for each chunk, in ascending order
    """
    for start in range(1, total_rows + 1, chunksize):
        yield start, min(start + chunksize - 1, total_rows)
