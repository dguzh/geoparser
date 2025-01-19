from abc import ABC, abstractmethod
from typing import List, Optional, Type, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(ABC):
    @property
    @abstractmethod
    def model(self) -> Type[T]:
        pass

    def create(self, db: Session, item: T) -> T:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def read(self, db: Session, id: str) -> Optional[T]:
        return db.get(self.model, id)

    def read_all(self, db: Session, **filters) -> List[T]:
        filter_args = [
            getattr(self.model, key) == value for key, value in filters.items()
        ]
        return db.exec(select(self.model).where(*filter_args)).all()

    def update(self, db: Session, item: T) -> T:
        db_item = db.get(self.model, item.id)
        if not db_item:
            raise ValueError(f"{self.model.__name__} with ID {item.id} not found.")
        item_data = item.model_dump(exclude_unset=True)
        for key, value in item_data.items():
            setattr(db_item, key, value)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    def delete(self, db: Session, id: str) -> Optional[T]:
        item = db.get(self.model, id)
        if not item:
            raise ValueError(f"{self.model.__name__} with ID {id} not found.")
        db.delete(item)
        db.commit()
        return item
