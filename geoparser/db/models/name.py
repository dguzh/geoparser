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


class NameFTS(SQLModel, table=True):
    """
    Read-only mapping to the name_fts virtual table.

    This provides access to the FTS5 virtual table with unicode61 tokenization
    for exact matching operations on names.
    """

    __tablename__ = "name_fts"

    rowid: int = Field(primary_key=True)
    text: str


class NameSpellfixVocab(SQLModel, table=True):
    """
    Read-only mapping to the name_spellfix_vocab shadow table.

    This provides access to the spellfix1 shadow table for fuzzy matching
    operations on names using phonetic hashing and edit distance.
    The shadow table is automatically maintained by the spellfix1 virtual table.
    """

    __tablename__ = "name_spellfix_vocab"

    id: int = Field(primary_key=True)
    word: str
    k2: str


class NameCreate(NameBase):
    """Model for creating a new name."""

    feature_id: int


class NameUpdate(SQLModel):
    """Model for updating an existing name."""

    id: int
    text: t.Optional[str] = None
    feature_id: t.Optional[int] = None


# Event listener to create virtual tables and triggers after name table creation
@event.listens_for(Name.__table__, "after_create")
def setup_virtual_tables(target, connection, **kw):
    """
    Create FTS and spellfix virtual tables and triggers for name search.

    This function is automatically called when the name table is created.
    It sets up:
    1. An FTS5 virtual table with unicode61 tokenization for exact matching
    2. A spellfix1 virtual table for fuzzy matching with edit distance
    3. Triggers to keep both tables in sync with the main name table

    Args:
        target: The table that was created (name table)
        connection: Database connection
        **kw: Additional keyword arguments
    """
    # Drop existing tables first (in case they were created by SQLModel)
    connection.execute(text("DROP TABLE IF EXISTS name_fts"))
    connection.execute(text("DROP TABLE IF EXISTS name_spellfix"))
    connection.execute(text("DROP TABLE IF EXISTS name_spellfix_vocab"))

    # Create FTS5 virtual table for exact matching with unicode61 tokenizer
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE name_fts USING fts5(
            text,
            content='',
            tokenize="unicode61 remove_diacritics 2 tokenchars '.'"
        )
    """
        )
    )

    # Create spellfix1 virtual table for fuzzy matching
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE name_spellfix USING spellfix1
    """
        )
    )

    # Create index on k2 column in shadow table for efficient lookups
    connection.execute(
        text(
            """
        CREATE INDEX IF NOT EXISTS idx_name_spellfix_vocab_k2 ON name_spellfix_vocab(k2)
    """
        )
    )

    # Create triggers for INSERT operations on FTS and spellfix tables
    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS name_fts_insert
        AFTER INSERT ON name
        BEGIN
            INSERT INTO name_fts(rowid, text) VALUES (new.id, new.text);
        END
    """
        )
    )

    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS name_spellfix_insert
        AFTER INSERT ON name
        BEGIN
            INSERT INTO name_spellfix(rowid, word) VALUES (new.id, new.text);
        END
    """
        )
    )
