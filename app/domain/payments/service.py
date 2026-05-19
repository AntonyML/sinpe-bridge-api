"""Lógica de negocio para mensajes SINPE recibidos desde la app móvil."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.payments.repository import SinpeMessageRepository
from app.domain.payments.schemas import SinpeMessageCreate, SinpeMessageResponse


class SinpeMessageService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SinpeMessageRepository(db)

    async def receive(self, data: SinpeMessageCreate) -> SinpeMessageResponse:
        message_id = uuid.UUID(data.envelope.message_id)

        # si ya existe ese message_id, devolver el que hay guardado
        existing = await self._repo.get_by_message_id(message_id)
        if existing:
            return SinpeMessageResponse.model_validate(existing)

        # Convertir unix timestamp del SMS a datetime con timezone
        message_timestamp: datetime | None = None
        if data.payload.timestamp:
            message_timestamp = datetime.fromtimestamp(
                data.payload.timestamp, tz=timezone.utc
            )

        msg = await self._repo.create(
            id_pos=data.id_pos,
            message_id=message_id,
            body=data.payload.body,
            sender=data.payload.sender,
            message_timestamp=message_timestamp,
            envelope=data.envelope.model_dump(),
            payload_raw=data.payload.model_dump(),
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
