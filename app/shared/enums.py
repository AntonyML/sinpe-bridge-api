from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    CONFIRMED = "confirmed"   # pago verificado y conciliado
    REVIEW = "review"         # requiere revisión manual
    EXPIRED = "expired"       # pago fuera de la ventana de tiempo
    REJECTED = "rejected"


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
