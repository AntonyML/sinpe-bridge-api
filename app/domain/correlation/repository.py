from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models import CorrelationSession

class CorrelationSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_token(self, id_pos: str, token: str) -> CorrelationSession | None:
        result = await self._db.execute(
            select(CorrelationSession)
            .join(CorrelationSession.order)
            .where(
                CorrelationSession.token == token,
                CorrelationSession.order.has(id_pos=id_pos),
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def create(
        self,
        order_id,
        token: str,
        expires_at: datetime,
        raw_message_id=None,
        sinpe_event_id=None,
        status: str = "pending",
        match_method: str = "none",
    ) -> CorrelationSession:
        if status == "matched":
            if sinpe_event_id is None and raw_message_id is not None:
                sinpe_event_id = raw_message_id
            matched_at = datetime.utcnow()
        else:
            matched_at = None

        session = CorrelationSession(
            order_id=order_id,
            sinpe_event_id=sinpe_event_id,
            token=token,
            expires_at=expires_at,
            raw_message_id=raw_message_id,
            status=status,
            match_method=match_method,
            matched_at=matched_at,
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def update_raw_message(self, session: CorrelationSession, raw_message_id) -> CorrelationSession:
        session.raw_message_id = raw_message_id
        session.sinpe_event_id = raw_message_id
        session.status = "matched"
        session.match_method = "token"
        session.matched_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(session)
        return session