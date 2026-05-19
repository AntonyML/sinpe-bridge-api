import json
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
        new_id = uuid.uuid4()
        products_json = json.dumps([p.model_dump() for p in data.products])

        async with self._db.bind.connect() as conn:
            raw = await conn.get_raw_connection()
            row = await raw.driver_connection.fetchrow("""
                INSERT INTO purchase_orders 
                    (id, order_number, id_pos, amount, status, payment_method, 
                     correlation_token, products, ordered_at, expires_at)
                VALUES 
                    ($1::uuid, $2, $3, $4, 
                     $5::order_status, $6::payment_method,
                     $7, $8::jsonb, $9, $10)
                RETURNING *
            """,
            str(new_id), data.order_number, data.id_pos, float(data.amount),
            "pending", data.payment_method, data.correlation_token,
            products_json, data.ordered_at, expires_at)

        return PurchaseOrder(
            id=row["id"],
            order_number=row["order_number"],
            id_pos=row["id_pos"],
            amount=float(row["amount"]),
            status=row["status"],
            payment_method=row["payment_method"],
            correlation_token=row["correlation_token"],
            products=row["products"],
            ordered_at=row["ordered_at"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )

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