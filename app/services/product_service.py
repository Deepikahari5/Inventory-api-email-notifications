from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.database import commit_or_conflict
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.product import Product
from app.repositories.catalog_repository import CategoryRepository, SupplierRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate, StockAdjustment


@dataclass
class InventoryEvent:
    product_name: str
    sku: str
    operation: str
    previous_quantity: int | None
    new_quantity: int | None
    reason: str | None = None


@dataclass
class ProductChange:
    product: Product
    low_stock_alert: bool = False
    event: InventoryEvent | None = None


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.products = ProductRepository(db)
        self.categories = CategoryRepository(db)
        self.suppliers = SupplierRepository(db)

    def create(self, payload: ProductCreate) -> ProductChange:
        if self.products.get_by_sku(payload.sku):
            raise ConflictError("SKU already exists")
        self._validate_references(payload.category_id, payload.supplier_id)
        product = Product(**payload.model_dump())
        alert = self._evaluate_low_stock(product)
        self.products.add(product)
        commit_or_conflict(self.db, "SKU already exists")
        return ProductChange(product=product, low_stock_alert=alert)

    def list(self, **filters) -> list[Product]:
        return self.products.search(**filters)

    def get(self, product_id: int) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    def update(self, product_id: int, payload: ProductUpdate) -> ProductChange:
        product = self.get(product_id)
        data = payload.model_dump(exclude_unset=True)
        new_sku = data.get("sku")
        if new_sku and new_sku != product.sku and self.products.get_by_sku(new_sku):
            raise ConflictError("SKU already exists")
        self._validate_references(data.get("category_id"), data.get("supplier_id"))
        for field, value in data.items():
            setattr(product, field, value)
        alert = self._evaluate_low_stock(product)
        commit_or_conflict(self.db, "SKU already exists")
        return ProductChange(product=product, low_stock_alert=alert)

    def adjust_stock(self, product_id: int, payload: StockAdjustment) -> ProductChange:
        product = self.get(product_id)
        previous = product.stock_quantity
        new_quantity = previous + payload.delta
        if new_quantity < 0:
            raise ValidationAppError("Stock quantity cannot become negative")
        product.stock_quantity = new_quantity
        alert = self._evaluate_low_stock(product)
        self.db.commit()
        event = InventoryEvent(
            product_name=product.name,
            sku=product.sku,
            operation="Stock adjustment",
            previous_quantity=previous,
            new_quantity=new_quantity,
            reason=payload.reason,
        )
        return ProductChange(product=product, low_stock_alert=alert, event=event)

    def delete(self, product_id: int) -> InventoryEvent:
        product = self.get(product_id)
        event = InventoryEvent(
            product_name=product.name,
            sku=product.sku,
            operation="Product deleted",
            previous_quantity=product.stock_quantity,
            new_quantity=None,
        )
        self.products.delete(product)
        self.db.commit()
        return event

    def _evaluate_low_stock(self, product: Product) -> bool:
        if product.stock_quantity <= product.reorder_level:
            if not product.low_stock_notified:
                product.low_stock_notified = True
                return True
            return False
        product.low_stock_notified = False
        return False

    def _validate_references(self, category_id: int | None, supplier_id: int | None) -> None:
        if category_id is not None and self.categories.get(category_id) is None:
            raise ValidationAppError("Category does not exist")
        if supplier_id is not None and self.suppliers.get(supplier_id) is None:
            raise ValidationAppError("Supplier does not exist")
