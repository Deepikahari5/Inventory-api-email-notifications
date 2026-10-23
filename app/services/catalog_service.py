from sqlalchemy.orm import Session

from app.core.database import commit_or_conflict
from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.models.supplier import Supplier
from app.repositories.catalog_repository import CategoryRepository, SupplierRepository
from app.schemas.catalog import CategoryCreate, CategoryUpdate, SupplierCreate, SupplierUpdate


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryRepository(db)

    def create(self, payload: CategoryCreate) -> Category:
        if self.repo.get_by_name(payload.name):
            raise ConflictError("Category name already exists")
        category = self.repo.add(Category(**payload.model_dump()))
        commit_or_conflict(self.db, "Category name already exists")
        return category

    def list(self, skip: int, limit: int) -> list[Category]:
        return self.repo.list(skip, limit)

    def get(self, category_id: int) -> Category:
        category = self.repo.get(category_id)
        if category is None:
            raise NotFoundError("Category not found")
        return category

    def update(self, category_id: int, payload: CategoryUpdate) -> Category:
        category = self.get(category_id)
        data = payload.model_dump(exclude_unset=True)
        new_name = data.get("name")
        if new_name and new_name != category.name and self.repo.get_by_name(new_name):
            raise ConflictError("Category name already exists")
        for field, value in data.items():
            setattr(category, field, value)
        commit_or_conflict(self.db, "Category name already exists")
        return category

    def delete(self, category_id: int) -> None:
        category = self.get(category_id)
        self.repo.delete(category)
        commit_or_conflict(self.db, "Category is still referenced by products")


class SupplierService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SupplierRepository(db)

    def create(self, payload: SupplierCreate) -> Supplier:
        if self.repo.get_by_name(payload.name):
            raise ConflictError("Supplier name already exists")
        supplier = self.repo.add(Supplier(**payload.model_dump()))
        commit_or_conflict(self.db, "Supplier name already exists")
        return supplier

    def list(self, skip: int, limit: int) -> list[Supplier]:
        return self.repo.list(skip, limit)

    def get(self, supplier_id: int) -> Supplier:
        supplier = self.repo.get(supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found")
        return supplier

    def update(self, supplier_id: int, payload: SupplierUpdate) -> Supplier:
        supplier = self.get(supplier_id)
        data = payload.model_dump(exclude_unset=True)
        new_name = data.get("name")
        if new_name and new_name != supplier.name and self.repo.get_by_name(new_name):
            raise ConflictError("Supplier name already exists")
        for field, value in data.items():
            setattr(supplier, field, value)
        commit_or_conflict(self.db, "Supplier name already exists")
        return supplier

    def delete(self, supplier_id: int) -> None:
        supplier = self.get(supplier_id)
        self.repo.delete(supplier)
        commit_or_conflict(self.db, "Supplier is still referenced by products")
