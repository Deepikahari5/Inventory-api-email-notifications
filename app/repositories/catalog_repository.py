from sqlalchemy import select

from app.models.category import Category
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    def get_by_name(self, name: str) -> Category | None:
        return self.db.scalar(select(Category).where(Category.name == name))


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    def get_by_name(self, name: str) -> Supplier | None:
        return self.db.scalar(select(Supplier).where(Supplier.name == name))
