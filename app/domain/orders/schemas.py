import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PaymentMethod(str, Enum):
    sinpe = "sinpe"
    card = "card"
    cash = "cash"
    transfer = "transfer"


class OrderProduct(BaseModel):
    code: str
    name: str
    price: float
    quantity: int
    line_total: float


class PurchaseOrderCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=100)
    id_pos: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0)
    payment_method: PaymentMethod = PaymentMethod.sinpe
    correlation_token: str | None = Field(default=None, max_length=8)
    products: list[OrderProduct] = []
    ordered_at: datetime
    expires_at: datetime | None = None


class PurchaseOrderResponse(BaseModel):
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
