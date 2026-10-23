from sqlalchemy import select

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    def get_by_sku(self, sku: str) -> Product | None:
        return self.db.scalar(select(Product).where(Product.sku == sku))

    def search(
        self,
        name: str | None = None,
        category_id: int | None = None,
        supplier_id: int | None = None,
        low_stock_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        statement = select(Product)
        if name:
            statement = statement.where(Product.name.ilike(f"%{name}%"))
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        if supplier_id is not None:
            statement = statement.where(Product.supplier_id == supplier_id)
        if low_stock_only:
            statement = statement.where(Product.stock_quantity <= Product.reorder_level)
        statement = statement.order_by(Product.id).offset(skip).limit(limit)
        return list(self.db.scalars(statement))
