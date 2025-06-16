import typing as t

from sqlalchemy import UniqueConstraint, event, text
from sqlmodel import Field, Relationship, SQLModel

if t.TYPE_CHECKING:
    from geoparser.db.models.feature import Feature


class ToponymBase(SQLModel):
    """Base model for toponym data."""

    toponym: str = Field(index=True)
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
        UniqueConstraint("toponym", "feature_id", name="uq_toponym_feature"),
    )

    id: int = Field(primary_key=True)
    feature: "Feature" = Relationship(back_populates="toponyms")


class ToponymFTS(SQLModel, table=True):
    """
    Read-only mapping to the toponym_fts virtual table.

    This provides access to the FTS5 virtual table for full-text search
    operations on toponyms with case-insensitive matching and text normalization.
    """

    __tablename__ = "toponym_fts"

    rowid: int = Field(primary_key=True)
    toponym: str


class ToponymCreate(ToponymBase):
    """Model for creating a new toponym."""


class ToponymUpdate(SQLModel):
    """Model for updating an existing toponym."""

    id: int
    toponym: t.Optional[str] = None
    feature_id: t.Optional[int] = None


# Event listener to create FTS table and triggers after toponym table creation
@event.listens_for(Toponym.__table__, "after_create")
def setup_fts(target, connection, **kw):
    """
    Create FTS virtual table and trigger for toponym full-text search.

    This function is automatically called when the toponym table is created.
    It sets up:
    1. An FTS5 virtual table for efficient text searching
    2. A trigger to keep the FTS table in sync with the main toponym table

    Args:
        target: The table that was created (toponym table)
        connection: Database connection
        **kw: Additional keyword arguments
    """
    # Create FTS5 virtual table for toponym search
    connection.execute(
        text(
            """
        CREATE VIRTUAL TABLE IF NOT EXISTS toponym_fts USING fts5(
            toponym,
            content='',
            tokenize="unicode61 tokenchars '.'"
        )
    """
        )
    )

    # Create trigger for INSERT operations
    connection.execute(
        text(
            """
        CREATE TRIGGER IF NOT EXISTS toponym_fts_insert 
        AFTER INSERT ON toponym 
        BEGIN
            INSERT INTO toponym_fts(rowid, toponym) VALUES (new.id, new.toponym);
        END
    """
        )
    )
