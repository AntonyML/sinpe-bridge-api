from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db


async def get_order_service(db: AsyncSession = Depends(get_db)):
    from app.domain.orders.service import OrderService
    return OrderService(db)


async def get_sinpe_message_service(db: AsyncSession = Depends(get_db)):
    from app.domain.payments.service import SinpeMessageService
    return SinpeMessageService(db)


async def get_upload_service(db: AsyncSession = Depends(get_db)):
    from app.domain.uploads.service import UploadService
    return UploadService(db)
