import typing as t

from sqlalchemy import UniqueConstraint, event, text
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature


class NameBase(SQLModel):
    """Base model for name data."""

    text: str = Field(index=True)


class Name(NameBase, table=True):
    """
    Represents a name associated with a gazetteer feature.

    A name maps place names (strings) to feature IDs. Multiple names can
    reference the same feature, and the same name can reference multiple features.

    This model automatically creates an FTS (Full-Text Search) virtual table
    for efficient partial matching of names.
    """

    __table_args__ = (UniqueConstraint("text", "feature_id", name="uq_name_feature"),)

    id: int = Field(primary_key=True)
    feature_id: int = Field(foreign_key="feature.id", index=True)
    feature: "Feature" = Relationship(back_populates="names")

    def __str__(self) -> str:
        """
        Return a string representation of the name.

        Returns:
            String with name indicator and text content
        """
        return f"Name({self.text})"

    def __repr__(self) -> str:
        """
        Return a developer representation of the name.

        Returns:
            Same as __str__ method
        """
        return self.__str__()


class NameFTSWords(SQLModel, table=True):
    """
    Read-only mapping to the name_fts_words virtual table.

    This provides access to the FTS5 virtual table with unicode61 tokenization
    for exact matching operations on names.
    """

    __tablename__ = "name_fts_words"

    rowid: int = Field(primary_key=True)
    text: str


class NameFTSTrigrams(SQLModel, table=True):
    """
    Read-only mapping to the name_fts_trigrams virtual table.

    This provides access to the FTS5 virtual table with trigram tokenization
    for partial and fuzzy matching operations on names with character-level
    matching capabilities.
    """

    __tablename__ = "name_fts_trigrams"

    rowid: int = Field(primary_key=True)
    text: str


class NameCreate(NameBase):
    """Model for creating a new name."""

    feature_id: int


class NameUpdate(SQLModel):
    """Model for updating an existing name."""

    id: int
    text: t.Optional[str] = None
    feature_id: t.Optional[int] = None


# Event listener to create FTS table and triggers after name table creation
@event.listens_for(Name.__table__, "after_create")
def setup_fts(target, connection, **kw):
    """
    Create FTS virtual tables and triggers for name full-text search.

    This function is automatically called when the name table is created.
    It sets up:
    1. An FTS5 virtual table with unicode61 tokenization for exact matching
    2. An FTS5 virtual table with trigram tokenization for partial/fuzzy matching
    3. Triggers to keep both FTS tables in sync with the main name table

    Args:
        target: The table that was created (name table)
        connection: Database connection
        **kw: Additional keyword arguments
    """
    # Drop any existing FTS tables first (in case they were created by SQLModel)
    connection.execute(text("DROP TABLE IF EXISTS name_fts_words"))
    connection.execute(text("DROP TABLE IF EXISTS name_fts_trigrams"))

    # Create FTS5 virtual table for exact matching with unicode61 tokenizer
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE name_fts_words USING fts5(
            text,
            content='',
            tokenize="unicode61 remove_diacritics 2 tokenchars '.'"
        )
    """
        )
    )

    # Create FTS5 virtual table for partial/fuzzy matching with trigram tokenizer
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE name_fts_trigrams USING fts5(
            text,
            content='',
            tokenize="trigram remove_diacritics 1"
        )
    """
        )
    )

    # Create triggers for INSERT operations on both FTS tables
    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS name_fts_words_insert
        AFTER INSERT ON name
        BEGIN
            INSERT INTO name_fts_words(rowid, text) VALUES (new.id, new.text);
        END
    """
        )
    )

    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS name_fts_trigrams_insert
        AFTER INSERT ON name
        BEGIN
            INSERT INTO name_fts_trigrams(rowid, text) VALUES (new.id, new.text);
        END
    """
        )
    )
