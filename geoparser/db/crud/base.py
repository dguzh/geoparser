import typing as t
import uuid
from typing import Generic, Type, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations for all models.
    """

    model: Type[T] = None

    @classmethod
    def create(cls, db: Session, obj_in: SQLModel) -> T:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Object to create (typically a Create model)

        Returns:
            Created object
        """
        # Convert input to model instance using the model's data
        data = obj_in.model_dump()
        db_obj = cls.model(**data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @classmethod
    def get(cls, db: Session, id: uuid.UUID) -> t.Optional[T]:
        """
        Get a record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Record if found, None otherwise
        """
        statement = select(cls.model).where(cls.model.id == id)
        return db.exec(statement).unique().first()

    @classmethod
    def get_all(cls, db: Session) -> t.List[T]:
        """
        Get all records.

        Args:
            db: Database session

        Returns:
            List of all records
        """
        statement = select(cls.model)
        return db.exec(statement).unique().all()

    @classmethod
    def update(cls, db: Session, *, db_obj: T, obj_in: SQLModel) -> T:
        """
        Update a record.

        Args:
            db: Database session
            db_obj: Existing database object
            obj_in: New data to update with

        Returns:
            Updated object
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @classmethod
    def delete(cls, db: Session, *, id: uuid.UUID) -> t.Optional[T]:
        """
        Delete a record.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Deleted object if found, None otherwise
        """
        obj = cls.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
