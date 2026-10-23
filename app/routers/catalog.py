from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_category_service, get_current_user, get_supplier_service, require_roles
from app.models.user import UserRole
from app.schemas.catalog import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)
from app.services.catalog_service import CategoryService, SupplierService

manager_or_admin = require_roles(UserRole.ADMIN, UserRole.MANAGER)
admin_only = require_roles(UserRole.ADMIN)

categories_router = APIRouter(prefix="/categories", tags=["Categories"])
suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@categories_router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    _=Depends(manager_or_admin),
):
    return service.create(payload)


@categories_router.get("", response_model=list[CategoryRead])
def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: CategoryService = Depends(get_category_service),
    _=Depends(get_current_user),
):
    return service.list(skip, limit)


@categories_router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    _=Depends(get_current_user),
):
    return service.get(category_id)


@categories_router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
    _=Depends(manager_or_admin),
):
    return service.update(category_id, payload)


@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    _=Depends(admin_only),
):
    service.delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@suppliers_router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    service: SupplierService = Depends(get_supplier_service),
    _=Depends(manager_or_admin),
):
    return service.create(payload)


@suppliers_router.get("", response_model=list[SupplierRead])
def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: SupplierService = Depends(get_supplier_service),
    _=Depends(get_current_user),
):
    return service.list(skip, limit)


@suppliers_router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: int,
    service: SupplierService = Depends(get_supplier_service),
    _=Depends(get_current_user),
):
    return service.get(supplier_id)


@suppliers_router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    service: SupplierService = Depends(get_supplier_service),
    _=Depends(manager_or_admin),
):
    return service.update(supplier_id, payload)


@suppliers_router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    service: SupplierService = Depends(get_supplier_service),
    _=Depends(admin_only),
):
    service.delete(supplier_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
