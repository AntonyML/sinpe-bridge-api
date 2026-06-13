import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.db.base import Base

# JSONB en Postgres (producción/Supabase) y JSON genérico en SQLite (dev).
# Permite que el mismo modelo corra en ambos motores.
JSONType = JSONB().with_variant(JSON(), "sqlite")


class PurchaseOrder(Base):
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
        SAEnum("pending", "matched", "confirmed", "review", "expired", "rejected",
               name="order_status", create_type=False),
        nullable=False, default="pending"
    )
    payment_method: Mapped[str] = mapped_column(
        SAEnum("sinpe", "card", "cash", "transfer",
               name="payment_method", create_type=False),
        nullable=False
    )
    correlation_token: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    # Lista de productos
    products: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default=list
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
    sinpe_messages: Mapped[list["SinpeRawMessage"]] = relationship(
        back_populates="purchase_order"
    )
    correlation_sessions: Mapped[list["CorrelationSession"]] = relationship(
        back_populates="order"
    )


class SinpeRawMessage(Base):

    __tablename__ = "sinpe_raw_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_pos: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    message_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Envelope completo enviado por la app (metadata de seguridad/trazabilidad)
    envelope: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    # Payload crudo completo enviado por la app
    payload_raw: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    # Número de referencia/comprobante SINPE extraído del mensaje.
    # Se usa para evitar que el mismo comprobante concilie dos órdenes distintas.
    reference: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # False = recién llegó, True = ya fue procesado por la lógica de comparación
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(
        back_populates="sinpe_messages"
    )
    correlation_sessions: Mapped[list["CorrelationSession"]] = relationship(
        back_populates="raw_message"
    )


class CorrelationSession(Base):
    __tablename__ = "correlation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False
    )
    sinpe_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "pending", "matched", "confirmed", "review", "unmatched", "expired",
            name="session_status", create_type=False
        ),
        nullable=False,
        default="pending",
    )
    confidence_score: Mapped[int | None] = mapped_column(nullable=True)
    match_method: Mapped[str] = mapped_column(
        SAEnum(
            "token", "scoring", "manual", "none",
            name="match_method", create_type=False
        ),
        nullable=False,
        default="none",
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sinpe_raw_messages.id"), nullable=True
    )
    matched_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    match_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["PurchaseOrder"] = relationship(back_populates="correlation_sessions")
    raw_message: Mapped["SinpeRawMessage | None"] = relationship(back_populates="correlation_sessions")
    image_receipts: Mapped[list["SinpeImageReceipt"]] = relationship(
        back_populates="correlation_session"
    )


class SinpeImageReceipt(Base):
    """
    Comprobante SINPE recibido como imagen.

    Modelo unificado de las dos ramas:
    - Campos de la subida basada en token + sesión de correlación
      (correlation_session_id, image_url, extracted_token, ...).
    - Campos del flujo OCR + conciliación (ocr_text, amount, reference,
      reconciliation_result, ...).

    Para que ambos flujos puedan insertar sin chocar, los campos NOT NULL que
    cada flujo no llena quedan como nullable (image_url, file_hash, upload_id).
    """
    __tablename__ = "sinpe_image_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_pos: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # --- Flujo token + sesión de correlación (rama HEAD) ---
    correlation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correlation_sessions.id"), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_metadata: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    extracted_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # --- Flujo OCR + conciliación (rama luis) ---
    upload_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ocr_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sender_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    bank: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reconciliation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    correlation_session: Mapped["CorrelationSession | None"] = relationship(
        back_populates="image_receipts"
    )
