"""
Pydantic schemas for upload operations.

Defines validation models for:
- Receipt image uploads
- QR code images
- Multipart form-data payloads
- Upload metadata
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class ImageType(str, Enum):
    """Supported image types for upload."""
    RECEIPT_QR = "receipt_qr"
    SINPE_SCREENSHOT = "sinpe_screenshot"
    BANK_TRANSFER_PROOF = "bank_transfer_proof"
    FRAUD_EVIDENCE = "fraud_evidence"


class ImageMetadata(BaseModel):
    """Metadata for uploaded images."""
    image_type: ImageType
    device_id: str
    timestamp: int = Field(..., description="Unix timestamp when image was captured")
    correlation_id: Optional[str] = None
    message_id: Optional[str] = None  # Reference to SMS if related
    
    class Config:
        use_enum_values = True


class UploadResponse(BaseModel):
    """Response after successful upload."""
    upload_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    file_size: int
    mime_type: str
    image_type: ImageType
    correlation_id: str
    message_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class UploadStatusResponse(BaseModel):
    """Check status of an upload."""
    upload_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float = Field(ge=0, le=100)
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class EnvelopeMetadata(BaseModel):
    """Secure envelope metadata for all API requests."""
    message_id: str = Field(..., description="Unique message identifier (UUID)")
    correlation_id: str = Field(..., description="Trace correlation ID")
    content_hash: str = Field(..., description="SHA-256 hash of payload")
    signature: str = Field(..., description="HMAC SHA-256 signature")
    created_at: int = Field(..., description="Unix timestamp of creation")
    source: str = Field(..., description="Source identifier (e.g., 'android-sms-listener')")
    device_hash: str = Field(..., description="Anonymized device hash")
    status: str = "SENT"
    
    class Config:
        use_enum_values = True


class ValidationError(BaseModel):
    """API validation error response."""
    error: str
    status: int
    request_id: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict] = None


class ImageReconciliationResponse(BaseModel):
    """Resultado de procesar un comprobante en imagen: OCR + conciliación."""
    upload_id: str
    receipt_id: Optional[str] = None

    # OCR
    ocr_confidence: Optional[float] = None

    # Campos extraídos del comprobante
    amount: Optional[float] = None
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    reference: Optional[str] = None
    bank: Optional[str] = None
    transaction_at: Optional[datetime] = None

    # Veredicto
    reconciliation_result: Optional[str] = None  # valor de ReconciliationResult
    order_number: Optional[str] = None
    detail: Optional[str] = None
