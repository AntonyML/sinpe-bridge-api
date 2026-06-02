from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fraud.rules import FraudEngine
from app.domain.payments.schemas import ParsedSinpeData
from app.infrastructure.db.models import PurchaseOrder, SinpeRawMessage
from app.shared.enums import FraudResult

VELOCITY_WINDOW_MINUTES = 5    # ventana para conteo de velocidad


class FraudService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._engine = FraudEngine()

    async def evaluate(
        self,
        id_pos: str,
        parsed: ParsedSinpeData,
    ) -> tuple[FraudResult, str]:
        now = datetime.now(timezone.utc)
        velocity_since = now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)

        # Pagos recientes al mismo POS (todos los mensajes recibidos)
        result = await self._db.execute(
            select(func.count()).where(
                SinpeRawMessage.id_pos == id_pos,
                SinpeRawMessage.received_at >= velocity_since,
            )
        )
        recent_count_pos: int = result.scalar() or 0

        # Promedio histórico del monto de órdenes del POS
        result = await self._db.execute(
            select(func.avg(PurchaseOrder.amount)).where(
                PurchaseOrder.id_pos == id_pos,
            )
        )
        avg_amount_pos: float | None = result.scalar()

        return self._engine.evaluate(
            parsed=parsed,
            recent_count_pos=recent_count_pos,
            avg_amount_pos=float(avg_amount_pos) if avg_amount_pos else None,
        )
