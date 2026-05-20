from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.orders.repository import OrderRepository
from app.domain.orders.schemas import PurchaseOrderCreate, PurchaseOrderResponse

class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = OrderRepository(db)

    async def create(self, data: PurchaseOrderCreate) -> PurchaseOrderResponse:
        # No permitir duplicados por order_number
        existing = await self._repo.get_by_order_number(data.order_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La orden '{data.order_number}' ya existe.",
            )
        order = await self._repo.create(data)
        return PurchaseOrderResponse.model_validate(order)

    async def get_by_order_number(self, order_number: str) -> PurchaseOrderResponse:
        order = await self._repo.get_by_order_number(order_number)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada.",
            )
        return PurchaseOrderResponse.model_validate(order)

    async def list_by_pos(
        self, id_pos: str, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrderResponse]:
        orders = await self._repo.list_by_pos(id_pos, limit=limit, offset=offset)
        return [PurchaseOrderResponse.model_validate(o) for o in orders]
