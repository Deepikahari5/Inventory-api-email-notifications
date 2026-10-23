from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.background.tasks import send_inventory_event_task, send_low_stock_alert_task
from app.dependencies import get_current_user, get_product_service, require_roles
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, StockAdjustment
from app.services.product_service import ProductChange, ProductService

router = APIRouter(prefix="/products", tags=["Products"])

manager_or_admin = require_roles(UserRole.ADMIN, UserRole.MANAGER)
admin_only = require_roles(UserRole.ADMIN)


def _schedule(change: ProductChange, background_tasks: BackgroundTasks, actor: User) -> None:
    if change.low_stock_alert:
        background_tasks.add_task(send_low_stock_alert_task, change.product.id)
    if change.event is not None:
        background_tasks.add_task(send_inventory_event_task, change.event, actor.username)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    background_tasks: BackgroundTasks,
    service: ProductService = Depends(get_product_service),
    actor: User = Depends(manager_or_admin),
):
    change = service.create(payload)
    _schedule(change, background_tasks, actor)
    return change.product


@router.get("", response_model=list[ProductRead])
def list_products(
    name: str | None = None,
    category_id: int | None = None,
    supplier_id: int | None = None,
    low_stock_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ProductService = Depends(get_product_service),
    _: User = Depends(get_current_user),
):
    return service.list(
        name=name,
        category_id=category_id,
        supplier_id=supplier_id,
        low_stock_only=low_stock_only,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _: User = Depends(get_current_user),
):
    return service.get(product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    background_tasks: BackgroundTasks,
    service: ProductService = Depends(get_product_service),
    actor: User = Depends(manager_or_admin),
):
    change = service.update(product_id, payload)
    _schedule(change, background_tasks, actor)
    return change.product


@router.post("/{product_id}/adjust-stock", response_model=ProductRead)
def adjust_stock(
    product_id: int,
    payload: StockAdjustment,
    background_tasks: BackgroundTasks,
    service: ProductService = Depends(get_product_service),
    actor: User = Depends(get_current_user),
):
    change = service.adjust_stock(product_id, payload)
    _schedule(change, background_tasks, actor)
    return change.product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    service: ProductService = Depends(get_product_service),
    actor: User = Depends(admin_only),
):
    event = service.delete(product_id)
    background_tasks.add_task(send_inventory_event_task, event, actor.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
