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


async def get_reconciliation_service(db: AsyncSession = Depends(get_db)):
    from app.domain.reconciliation.service import ReconciliationService
    return ReconciliationService(db)


async def get_image_analyzer(db: AsyncSession = Depends(get_db)):
    from app.infrastructure.ai.sinpe_image_analyzer import SinpeImageAnalyzer
    return SinpeImageAnalyzer(db)
