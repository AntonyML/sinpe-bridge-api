import uuid
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.orders.schemas import PurchaseOrderCreate
from app.infrastructure.db.models import PurchaseOrder
from app.shared.constants import PAYMENT_WINDOW_MINUTES

class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, data: PurchaseOrderCreate) -> PurchaseOrder:
        expires_at = data.expires_at or (
            data.ordered_at + timedelta(minutes=PAYMENT_WINDOW_MINUTES)
        )
        order = PurchaseOrder(
            order_number=data.order_number,
            id_pos=data.id_pos,
            amount=data.amount,
            status="pending",
            payment_method=data.payment_method,
            correlation_token=data.correlation_token,
            products=[p.model_dump() for p in data.products],
            ordered_at=data.ordered_at,
            expires_at=expires_at,
        )
        self._db.add(order)
        await self._db.commit()
        await self._db.refresh(order)
        return order

    async def get_by_order_number(self, order_number: str) -> PurchaseOrder | None:
        result = await self._db.execute(
            select(PurchaseOrder).where(PurchaseOrder.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, order_id: uuid.UUID) -> PurchaseOrder | None:
        result = await self._db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_by_pos(
        self, id_pos: str, limit: int = 50, offset: int = 0
    ) -> list[PurchaseOrder]:
        result = await self._db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id_pos == id_pos)
            .order_by(PurchaseOrder.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())