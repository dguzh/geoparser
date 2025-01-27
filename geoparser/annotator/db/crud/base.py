import typing as t
from abc import ABC, abstractmethod

from sqlmodel import Session, SQLModel, select

T = t.TypeVar("T", bound=SQLModel)


class BaseRepository(ABC):
    model: t.Type[T]

    @classmethod
    def get_db_item(cls, db: Session, id: str) -> T:
        db_item = db.get(cls.model, id)
        if not db_item:
            raise ValueError(f"{cls.model.__name__} with ID {id} not found.")
        return db_item

    @classmethod
    def create(cls, db: Session, item: T) -> T:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def upsert(cls, db: Session, item: T, match_keys: t.List[str] = ["id"]) -> T:
        filter_args = [
            getattr(cls.model, key) == getattr(item, key) for key in match_keys
        ]
        existing_item = db.exec(select(cls.model).where(*filter_args)).first()
        if existing_item:
            item_data = item.model_dump(exclude_unset=True)
            for key, value in item_data.items():
                setattr(existing_item, key, value)
            return cls.update(db, existing_item)
        else:
            return cls.create(db, item)

    @classmethod
    def read(cls, db: Session, id: str) -> t.Optional[T]:
        return cls.get_db_item(db, id)

    @classmethod
    def read_all(cls, db: Session, **filters) -> t.List[T]:
        filter_args = [
            getattr(cls.model, key) == value for key, value in filters.items()
        ]
        return db.exec(select(cls.model).where(*filter_args)).all()

    @classmethod
    def update(cls, db: Session, item: T) -> T:
        db_item = cls.get_db_item(db, item.id)
        item_data = item.model_dump(exclude_unset=True)
        for key, value in item_data.items():
            setattr(db_item, key, value)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @classmethod
    def delete(cls, db: Session, id: str) -> t.Optional[T]:
        item = cls.get_db_item(db, id)
        db.delete(item)
        db.commit()
        return item
