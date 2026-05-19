from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNDER_REVIEW = "under_review"


class PaymentMethod(str, Enum):
    SINPE = "sinpe"
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
