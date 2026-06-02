import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.correlation.repository import CorrelationSessionRepository
from app.domain.orders.repository import OrderRepository
from app.domain.payments.repository import SinpeMessageRepository
from app.domain.payments.schemas import SinpeMessageCreate, SinpeMessageResponse

class SinpeMessageService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = SinpeMessageRepository(db)
        self._order_repo = OrderRepository(db)
        self._correlation_repo = CorrelationSessionRepository(db)

    async def receive(self, data: SinpeMessageCreate) -> SinpeMessageResponse:
        message_id = uuid.UUID(data.envelope.message_id)

        existing = await self._repo.get_by_message_id(message_id)
        if existing:
            return SinpeMessageResponse.model_validate(existing)

        message_timestamp: datetime | None = None
        if data.payload.timestamp:
            message_timestamp = datetime.fromtimestamp(
                data.payload.timestamp, tz=timezone.utc
            )

        order = await self._order_repo.get_by_pos_and_token(
            data.id_pos, data.correlation_token
        )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró una orden para el id_pos y correlation_token enviados.",
            )

        msg = await self._repo.create(
            id_pos=data.id_pos,
            message_id=message_id,
            body=data.payload.body,
            sender=data.payload.sender,
            message_timestamp=message_timestamp,
            envelope=data.envelope.model_dump(),
            payload_raw=data.payload.model_dump(),
            purchase_order_id=order.id,
            processed=True,
        )

        session = await self._correlation_repo.get_by_token(
            data.id_pos, data.correlation_token
        )

        if session:
            await self._correlation_repo.update_raw_message(session, msg.id)
        else:
            session = await self._correlation_repo.create(
                order_id=order.id,
                token=data.correlation_token,
                expires_at=order.expires_at,
                raw_message_id=msg.id,
                status="matched",
                match_method="token",
            )

        return SinpeMessageResponse.model_validate(msg)

    async def get_by_message_id(self, message_id: uuid.UUID) -> SinpeMessageResponse:
        msg = await self._repo.get_by_message_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensaje no encontrado.",
            )
        return SinpeMessageResponse.model_validate(msg)

    async def list_by_pos(
        self, id_pos: str, limit: int = 50, offset: int = 0
    ) -> list[SinpeMessageResponse]:
        messages = await self._repo.list_by_pos(id_pos, limit=limit, offset=offset)
        return [SinpeMessageResponse.model_validate(m) for m in messages]
