import re
import uuid
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.orders.schemas import PurchaseOrderCreate
from app.infrastructure.db.models import PurchaseOrder
from app.shared.constants import MAX_AMOUNT_DIFF, PAYMENT_WINDOW_MINUTES
from app.shared.enums import OrderStatus

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

    async def get_by_pos_and_token(
        self, id_pos: str, correlation_token: str
    ) -> PurchaseOrder | None:
        result = await self._db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id_pos == id_pos,
                PurchaseOrder.correlation_token == correlation_token,
            )
        )
        row = result.scalar_one_or_none()
        return row

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

    async def _pending_orders(self, id_pos: str) -> list[PurchaseOrder]:
        """Órdenes aún sin pagar de un POS, de la más reciente a la más antigua."""
        result = await self._db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id_pos == id_pos,
                PurchaseOrder.status == OrderStatus.PENDING.value,
            )
            .order_by(PurchaseOrder.ordered_at.desc())
        )
        return list(result.scalars().all())

    async def find_pending_by_token(
        self, id_pos: str, phone: str
    ) -> PurchaseOrder | None:
        """
        Busca una orden pendiente cuyo correlation_token coincida con el
        teléfono de quien paga.
        """
        target = re.sub(r"\D", "", phone)[-8:]
        for order in await self._pending_orders(id_pos):
            if not order.correlation_token:
                continue
            if re.sub(r"\D", "", order.correlation_token)[-8:] == target:
                return order
        return None

    async def find_pending_by_amount(
        self, id_pos: str, amount: float
    ) -> PurchaseOrder | None:
        """Busca una orden pendiente cuyo monto coincida (dentro de la tolerancia)."""
        for order in await self._pending_orders(id_pos):
            if abs(float(order.amount) - amount) <= MAX_AMOUNT_DIFF:
                return order
        return None

    async def update_status(
        self, order_id: uuid.UUID, status: OrderStatus | str
    ) -> None:
        """Actualiza el estado de una orden."""
        order = await self.get_by_id(order_id)
        if order is None:
            return
        order.status = status.value if isinstance(status, OrderStatus) else status
        await self._db.commit()