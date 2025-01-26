import typing as t
from abc import ABC, abstractmethod

from sqlmodel import Session, SQLModel, select

T = t.TypeVar("T", bound=SQLModel)


class BaseRepository(ABC):
    @property
    @abstractmethod
    def model(self) -> t.Type[T]:
        pass

    def get_db_item(self, db: Session, id: str) -> T:
        db_item = db.get(self.model, id)
        if not db_item:
            raise ValueError(f"{self.model.__name__} with ID {id} not found.")
        return db_item

    def create(self, db: Session, item: T) -> T:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def upsert(self, db: Session, item: T, match_keys: t.List[str] = ["id"]) -> T:
        filter_args = [
            getattr(self.model, key) == getattr(item, key) for key in match_keys
        ]
        existing_item = db.exec(select(self.model).where(*filter_args)).first()
        if existing_item:
            item_data = item.model_dump(exclude_unset=True)
            for key, value in item_data.items():
                setattr(existing_item, key, value)
            return self.update(db, existing_item)
        else:
            return self.create(db, item)

    def read(self, db: Session, id: str) -> t.Optional[T]:
        return self.get_db_item(db, id)

    def read_all(self, db: Session, **filters) -> t.List[T]:
        filter_args = [
            getattr(self.model, key) == value for key, value in filters.items()
        ]
        return db.exec(select(self.model).where(*filter_args)).all()

    def update(self, db: Session, item: T) -> T:
        db_item = self.get_db_item(db, item.id)
        item_data = item.model_dump(exclude_unset=True)
        for key, value in item_data.items():
            setattr(db_item, key, value)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    def delete(self, db: Session, id: str) -> t.Optional[T]:
        item = self.get_db_item(db, id)
        db.delete(item)
        db.commit()
        return item
