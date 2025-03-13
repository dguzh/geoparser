import typing as t
import uuid
from typing import Generic, Type, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations for all models.
    """

    def __init__(self, model: Type[T]):
        self.model = model

    def create(self, db: Session, obj_in: SQLModel) -> T:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Object to create

        Returns:
            Created object
        """
        db_obj = self.model.from_orm(obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: uuid.UUID) -> t.Optional[T]:
        """
        Get a record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Record if found, None otherwise
        """
        return db.get(self.model, id)

    def get_all(self, db: Session) -> t.List[T]:
        """
        Get all records.

        Args:
            db: Database session

        Returns:
            List of all records
        """
        statement = select(self.model)
        return db.exec(statement).all()

    def update(self, db: Session, *, db_obj: T, obj_in: SQLModel) -> T:
        """
        Update a record.

        Args:
            db: Database session
            db_obj: Existing database object
            obj_in: New data to update with

        Returns:
            Updated object
        """
        update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: uuid.UUID) -> t.Optional[T]:
        """
        Delete a record.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Deleted object if found, None otherwise
        """
        obj = db.get(self.model, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
