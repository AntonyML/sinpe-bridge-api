import uuid
from datetime import datetime
from pydantic import BaseModel

class OrderProduct(BaseModel):
    code: str
    name: str
    price: float
    quantity: int
    line_total: float

class PurchaseOrderCreate(BaseModel):
    # Lo que el POS manda al registrar una orden
    order_number: str
    id_pos: str
    amount: float
    payment_method: str
    correlation_token: str | None = None
    products: list[OrderProduct]
    ordered_at: datetime
    expires_at: datetime | None = None

class PurchaseOrderResponse(BaseModel):
    # Lo que la API devuelve al POS
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
