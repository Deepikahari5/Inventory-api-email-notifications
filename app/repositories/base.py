from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get(self, object_id: int) -> T | None:
        return self.db.get(self.model, object_id)

    def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        statement = select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement))

    def add(self, instance: T) -> T:
        self.db.add(instance)
        self.db.flush()
        return instance

    def delete(self, instance: T) -> None:
        self.db.delete(instance)
        self.db.flush()
