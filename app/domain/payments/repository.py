"""Acceso a datos para sinpe_raw_messages."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SinpeRawMessage


class SinpeMessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        id_pos: str,
        message_id: uuid.UUID,
        body: str,
        sender: str | None,
        message_timestamp: datetime | None,
        envelope: dict,
        payload_raw: dict,
    ) -> SinpeRawMessage:
        msg = SinpeRawMessage(
            id_pos=id_pos,
            message_id=message_id,
            body=body,
            sender=sender,
            message_timestamp=message_timestamp,
            envelope=envelope,
            payload_raw=payload_raw,
            processed=False,
        )
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_by_message_id(
        self, message_id: uuid.UUID
    ) -> SinpeRawMessage | None:
        result = await self._db.execute(
            select(SinpeRawMessage).where(
                SinpeRawMessage.message_id == message_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, msg_id: uuid.UUID) -> SinpeRawMessage | None:
        result = await self._db.execute(
            select(SinpeRawMessage).where(SinpeRawMessage.id == msg_id)
        )
        return result.scalar_one_or_none()

    async def list_by_pos(
        self, id_pos: str, limit: int = 50, offset: int = 0
    ) -> list[SinpeRawMessage]:
        result = await self._db.execute(
            select(SinpeRawMessage)
            .where(SinpeRawMessage.id_pos == id_pos)
            .order_by(SinpeRawMessage.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
