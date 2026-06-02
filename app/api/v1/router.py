from fastapi import APIRouter

from app.api.v1.endpoints import kiosk, orders, payments, uploads

api_router = APIRouter()
api_router.include_router(kiosk.router, prefix="/kiosk", tags=["Kiosk"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(uploads.router, tags=["Uploads"])
