"""Acceso a datos para sinpe_image_receipts (comprobantes en imagen)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import SinpeImageReceipt


class ImageReceiptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, **fields) -> SinpeImageReceipt:
        receipt = SinpeImageReceipt(**fields)
        self._db.add(receipt)
        await self._db.commit()
        await self._db.refresh(receipt)
        return receipt

    async def get_by_id(self, receipt_id: uuid.UUID) -> SinpeImageReceipt | None:
        result = await self._db.execute(
            select(SinpeImageReceipt).where(SinpeImageReceipt.id == receipt_id)
        )
        return result.scalar_one_or_none()

    async def hash_exists(self, file_hash: str) -> bool:
        """True si esa misma imagen (por hash) ya fue procesada antes."""
        result = await self._db.execute(
            select(SinpeImageReceipt.id).where(
                SinpeImageReceipt.file_hash == file_hash
            )
        )
        return result.first() is not None

    async def reference_exists(self, reference: str) -> bool:
        """True si esa referencia SINPE ya fue usada por otro comprobante en imagen."""
        result = await self._db.execute(
            select(SinpeImageReceipt.id).where(
                SinpeImageReceipt.reference == reference
            )
        )
        return result.first() is not None
