from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


router = APIRouter()


class OrderProduct(BaseModel):
	code: str = Field(min_length=1)
	name: str = Field(min_length=1)
	price: float = Field(ge=0)
	quantity: int = Field(ge=1)
	line_total: float = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
	order_number: str = Field(min_length=1)
	status: Literal["paid", "pending", "cancelled"]
	payment_method: Literal["sinpe", "cash", "card", "transfer"]
	ordered_at: datetime
	products: list[OrderProduct] = Field(min_length=1)
	amount: float = Field(ge=0)


class PurchaseOrderResponse(PurchaseOrderCreate):
	pass


HARDCODED_ORDERS: list[PurchaseOrderResponse] = [
	PurchaseOrderResponse(
		order_number="ORD-20260426-0001",
		status="paid",
		payment_method="sinpe",
		ordered_at=datetime(2026, 4, 26, 14, 22, 0),
		products=[
			OrderProduct(
				code="PROD001",
				name="Laptop Dell XPS 13",
				price=1299.99,
				quantity=1,
				line_total=1299.99,
			)
		],
		amount=1299.99,
	),
	PurchaseOrderResponse(
		order_number="ORD-20260428-0002",
		status="pending",
		payment_method="card",
		ordered_at=datetime(2026, 4, 28, 9, 15, 0),
		products=[
			OrderProduct(
				code="PROD010",
				name="Mouse Logitech MX Master 3S",
				price=109.99,
				quantity=2,
				line_total=219.98,
			)
		],
		amount=219.98,
	),
]


@router.get("", response_model=list[PurchaseOrderResponse])
def list_orders() -> list[PurchaseOrderResponse]:
	return HARDCODED_ORDERS


@router.get("/{order_number}", response_model=PurchaseOrderResponse)
def get_order(order_number: str) -> PurchaseOrderResponse:
	for order in HARDCODED_ORDERS:
		if order.order_number == order_number:
			return order

	raise HTTPException(
		status_code=status.HTTP_404_NOT_FOUND,
		detail="Order not found",
	)


@router.post(
	"",
	response_model=PurchaseOrderResponse,
	status_code=status.HTTP_201_CREATED,
)
def create_order(payload: PurchaseOrderCreate) -> PurchaseOrderResponse:
	for order in HARDCODED_ORDERS:
		if order.order_number == payload.order_number:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Order already exists",
			)

	created_order = PurchaseOrderResponse(**payload.model_dump())
	HARDCODED_ORDERS.append(created_order)
	return created_order
