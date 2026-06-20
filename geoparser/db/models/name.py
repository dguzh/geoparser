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


class NameSoundex(SQLModel, table=True):
    """
    Read-only mapping to the name_soundex table.

    This provides access to the Soundex codes used for fuzzy matching. Each row
    maps a name id to the Soundex code of its text, enabling phonetic candidate
    retrieval before rapidfuzz ranking. The table is maintained by a trigger on
    the name table.
    """

    __tablename__ = "name_soundex"

    id: int = Field(primary_key=True)
    code: str


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
    Create the FTS virtual table, soundex table, and triggers for name search.

    This function is automatically called when the name table is created.
    It sets up:
    1. An FTS5 virtual table with unicode61 tokenization for exact matching
    2. A soundex table for phonetic candidate retrieval in fuzzy matching
    3. Triggers to keep both tables in sync with the main name table

    Args:
        target: The table that was created (name table)
        connection: Database connection
        **kw: Additional keyword arguments
    """
    # Drop existing tables first (in case they were created by SQLModel)
    connection.execute(text("DROP TABLE IF EXISTS name_fts"))
    connection.execute(text("DROP TABLE IF EXISTS name_soundex"))

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

    # Create soundex table for fuzzy matching candidate retrieval
    connection.execute(
        text(
            """
        CREATE TABLE name_soundex (
            id INTEGER PRIMARY KEY,
            code TEXT
        )
    """
        )
    )

    # Create index on code column for efficient candidate lookups
    connection.execute(
        text(
            """
        CREATE INDEX IF NOT EXISTS idx_name_soundex_code ON name_soundex(code)
    """
        )
    )

    # Create triggers for INSERT operations on FTS and soundex tables
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
        CREATE TRIGGER IF NOT EXISTS name_soundex_insert
        AFTER INSERT ON name
        BEGIN
            INSERT INTO name_soundex(id, code) VALUES (new.id, soundex(new.text));
        END
    """
        )
    )
