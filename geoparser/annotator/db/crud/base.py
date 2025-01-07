import typing as t
from abc import ABC

from sqlmodel import Session, SQLModel, select


class BaseRepository(ABC):
    model = t.Type[SQLModel]

    def create(self, db: Session, item: t.Type[SQLModel]):
        db.add(item)
        db.commit()

    def read(self, db: Session, item: t.Type[SQLModel]):
        item = db.get(self.model, item.id)
        return item

    def read_all(self, db: Session):
        items = db.exec(select(self.model)).all()
        return items

    def update(self, db: Session, item: t.Type[SQLModel]):
        db_item = db.get(self.model, item.id)
        item_data = item.model_dump(exclude_unset=True)
        db_item.sqlmodel_update(item_data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

    def overwrite(self, db: Session, item: t.Type[SQLModel]):
        self.update(db, item)

    def delete(self, db: Session, item: t.Type[SQLModel]):
        item = db.get(self.model, item.id)
        db.delete(item)
        db.commit()
