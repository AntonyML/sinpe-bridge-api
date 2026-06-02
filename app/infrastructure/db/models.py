import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.db.base import Base


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
    envelope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    payload_raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
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
    __tablename__ = "sinpe_image_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    correlation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correlation_sessions.id"), nullable=True
    )
    id_pos: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    extracted_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    correlation_session: Mapped["CorrelationSession | None"] = relationship(
        back_populates="image_receipts"
    )
