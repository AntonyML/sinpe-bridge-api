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


class ReconciliationResult(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    UNDER_REVIEW = "under_review"
    EXPIRED = "expired"
    NO_ORDER_FOUND = "no_order_found"
    FRAUD = "fraud"


class FraudResult(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
