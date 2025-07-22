import typing as t

from sqlalchemy import UniqueConstraint, event, text
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature


class ToponymBase(SQLModel):
    """Base model for toponym data."""

    text: str = Field(index=True)
    feature_id: int = Field(foreign_key="feature.id", index=True)


class Toponym(ToponymBase, table=True):
    """
    Represents a toponym associated with a gazetteer feature.

    A toponym maps place names (strings) to feature IDs. Multiple toponyms can
    reference the same feature, and the same toponym can reference multiple features.

    This model automatically creates an FTS (Full-Text Search) virtual table
    for efficient partial matching of toponyms.
    """

    __table_args__ = (
        UniqueConstraint("text", "feature_id", name="uq_toponym_feature"),
    )

    id: int = Field(primary_key=True)
    feature: "Feature" = Relationship(back_populates="toponyms")


class ToponymFTSWords(SQLModel, table=True):
    """
    Read-only mapping to the toponym_fts_words virtual table.

    This provides access to the FTS5 virtual table with unicode61 tokenization
    for exact matching operations on toponyms.
    """

    __tablename__ = "toponym_fts_words"

    rowid: int = Field(primary_key=True)
    text: str


class ToponymFTSTrigrams(SQLModel, table=True):
    """
    Read-only mapping to the toponym_fts_trigrams virtual table.

    This provides access to the FTS5 virtual table with trigram tokenization
    for partial and fuzzy matching operations on toponyms with character-level
    matching capabilities.
    """

    __tablename__ = "toponym_fts_trigrams"

    rowid: int = Field(primary_key=True)
    text: str


class ToponymCreate(ToponymBase):
    """Model for creating a new toponym."""


class ToponymUpdate(SQLModel):
    """Model for updating an existing toponym."""

    id: int
    text: t.Optional[str] = None
    feature_id: t.Optional[int] = None


# Event listener to create FTS table and triggers after toponym table creation
@event.listens_for(Toponym.__table__, "after_create")
def setup_fts(target, connection, **kw):
    """
    Create FTS virtual tables and triggers for toponym full-text search.

    This function is automatically called when the toponym table is created.
    It sets up:
    1. An FTS5 virtual table with unicode61 tokenization for exact matching
    2. An FTS5 virtual table with trigram tokenization for partial/fuzzy matching
    3. Triggers to keep both FTS tables in sync with the main toponym table

    Args:
        target: The table that was created (toponym table)
        connection: Database connection
        **kw: Additional keyword arguments
    """
    # Drop any existing FTS tables first (in case they were created by SQLModel)
    connection.execute(text("DROP TABLE IF EXISTS toponym_fts_words"))
    connection.execute(text("DROP TABLE IF EXISTS toponym_fts_trigrams"))

    # Create FTS5 virtual table for exact matching with unicode61 tokenizer
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE toponym_fts_words USING fts5(
            text,
            content='',
            tokenize='unicode61 remove_diacritics 2 tokenchars "."'
        )
    """
        )
    )

    # Create FTS5 virtual table for partial/fuzzy matching with trigram tokenizer
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE toponym_fts_trigrams USING fts5(
            text,
            content='',
            tokenize='trigram remove_diacritics 1'
        )
    """
        )
    )

    # Create triggers for INSERT operations on both FTS tables
    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS toponym_fts_words_insert 
        AFTER INSERT ON toponym 
        BEGIN
            INSERT INTO toponym_fts_words(rowid, text) VALUES (new.id, new.text);
        END
    """
        )
    )

    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS toponym_fts_trigrams_insert 
        AFTER INSERT ON toponym 
        BEGIN
            INSERT INTO toponym_fts_trigrams(rowid, text) VALUES (new.id, new.text);
        END
    """
        )
    )
