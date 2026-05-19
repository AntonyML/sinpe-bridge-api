"""
Schemas para purchase_orders.
El POS usa estos contratos para comunicarse con la API.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OrderProduct(BaseModel):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    quantity: int = Field(ge=1)
    line_total: float = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    """Lo que el POS manda al registrar una orden."""
    order_number: str = Field(min_length=1, max_length=64)
    id_pos: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0)
    payment_method: Literal["sinpe", "cash", "card", "transfer"]
    # Teléfono del cliente — necesario para luego asociar el pago SINPE
    correlation_token: str | None = Field(default=None, max_length=20)
    products: list[OrderProduct] = Field(min_length=1)
    ordered_at: datetime
    expires_at: datetime | None = None


class PurchaseOrderResponse(BaseModel):
    """Lo que la API devuelve al POS."""
    id: uuid.UUID
    order_number: str
    id_pos: str
    amount: float
    status: str
    payment_method: str
    correlation_token: str | None
    products: list[OrderProduct]
    ordered_at: datetime
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
