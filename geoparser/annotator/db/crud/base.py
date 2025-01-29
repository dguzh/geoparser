import typing as t
from abc import ABC, abstractmethod

from sqlmodel import Session, SQLModel, select

T = t.TypeVar("T", bound=SQLModel)


class BaseRepository(ABC):
    model: t.Type[T]

    @classmethod
    def get_mapped_class(
        cls,
        item: T,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> T:
        item_data = item.model_dump(exclude=exclude, exclude_unset=True)
        return cls.model(**item_data, **additional)

    @classmethod
    def get_db_item(cls, db: Session, id: str) -> T:
        db_item = db.get(cls.model, id)
        if not db_item:
            raise ValueError(f"{cls.model.__name__} with ID {id} not found.")
        return db_item

    @classmethod
    def create(
        cls,
        db: Session,
        item: T,
        exclude: t.Optional[list[str]] = [],
        additional: t.Optional[dict[str, t.Any]] = {},
    ) -> T:
        item = cls.get_mapped_class(item, exclude, additional)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

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
