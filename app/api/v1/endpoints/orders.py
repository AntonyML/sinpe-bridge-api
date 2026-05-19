from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_order_service
from app.domain.orders.schemas import PurchaseOrderCreate, PurchaseOrderResponse
from app.domain.orders.service import OrderService

router = APIRouter()


@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="El POS registra una nueva orden de compra",
)
async def create_order(
    payload: PurchaseOrderCreate,
    service: OrderService = Depends(get_order_service),
) -> PurchaseOrderResponse:
    return await service.create(payload)


@router.get(
    "/{order_number}",
    response_model=PurchaseOrderResponse,
    summary="Consultar una orden por su numero",
)
async def get_order(
    order_number: str,
    service: OrderService = Depends(get_order_service),
) -> PurchaseOrderResponse:
    return await service.get_by_order_number(order_number)


@router.get(
    "",
    response_model=list[PurchaseOrderResponse],
    summary="Listar todas las ordenes de un POS",
)
async def list_orders(
    id_pos: str = Query(..., description="Identificador del POS"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: OrderService = Depends(get_order_service),
) -> list[PurchaseOrderResponse]:
    return await service.list_by_pos(id_pos, limit=limit, offset=offset)
