
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class PurchaseOrder(Base):
    """
    Orden de compra registrada por el POS.
    Se crea cuando el cliente va a pagar con SINPE.
    """
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    id_pos: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    # Teléfono del cliente — sirve para luego correlacionar con el pago SINPE
    correlation_token: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    # Lista de productos 
    products: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list
    )
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relación con los mensajes SINPE que se asocien a esta orden (se llena después)
    sinpe_messages: Mapped[list["SinpeRawMessage"]] = relationship(
        back_populates="purchase_order"
    )


class SinpeRawMessage(Base):
   
    __tablename__ = "sinpe_raw_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_pos: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    # UUID único generado por la app móvil
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    # Texto crudo del SMS enviado por el banco
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Número del banco que envió el SMS
    sender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Timestamp del SMS según el sistema operativo del teléfono
    message_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Envelope completo enviado por la app (metadata de seguridad/trazabilidad)
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Payload crudo completo enviado por la app
    payload_raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # False = recién llegó, True = ya fue procesado por la lógica de comparación
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Cuándo lo recibió la API
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Se llena después de la comparación, apunta a la orden que coincidió
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(
        back_populates="sinpe_messages"
    )
