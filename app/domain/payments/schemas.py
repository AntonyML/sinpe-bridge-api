import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SinpeEnvelope(BaseModel):
    content_hash: str
    correlation_id: str
    created_at: int
    device_hash: str
    message_id: str
    retry_count: int = 0
    signature: str
    source: str
    status: str
    version: str = "1.0"


class SinpeDebug(BaseModel):
    format: str | None = None
    pdu: str | None = None


class SinpeDevice(BaseModel):
    sim_slot: int | None = None
    subscription_id: int | None = None


class SinpeMetadata(BaseModel):
    protocol_id: int | None = None
    service_center: str | None = None
    status: int | None = None


class SinpeMultipart(BaseModel):
    ref: int = 0
    seq: int = 1
    total: int = 1


class SinpePayload(BaseModel):
    body: str
    debug: SinpeDebug | None = None
    device: SinpeDevice | None = None
    metadata: SinpeMetadata | None = None
    multipart: SinpeMultipart | None = None
    sender: str | None = None
    timestamp: int | None = None
 

class SinpeMessageCreate(BaseModel):
    id_pos: str = Field(min_length=1, max_length=64)
    correlation_token: str = Field(min_length=1, max_length=64)
    envelope: SinpeEnvelope
    payload: SinpePayload


class SinpeMessageResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    id_pos: str
    body: str
    sender: str | None
    message_timestamp: datetime | None
    processed: bool
    received_at: datetime
    purchase_order_id: uuid.UUID | None

    model_config = {"from_attributes": True}
