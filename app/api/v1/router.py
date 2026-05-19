from fastapi import APIRouter

from app.api.v1.endpoints import orders, payments

api_router = APIRouter()
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
