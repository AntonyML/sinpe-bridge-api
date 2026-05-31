from datetime import datetime, timedelta, timezone
import secrets
import string

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.shared.constants import PAYMENT_WINDOW_MINUTES

router = APIRouter()

TOKEN_ALPHABET = string.ascii_uppercase + string.digits
TOKEN_LENGTH = 5


class KioskTokenRequest(BaseModel):
    kiosk_id: str = Field(min_length=1, max_length=64)
    channel: str | None = Field(default="kiosk", max_length=32)
    source: str | None = Field(default="sinpe-bridge-kiosk", max_length=64)
    requested_at: datetime | None = None


class KioskTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    message: str
    kiosk_id: str


def generate_token(length: int = TOKEN_LENGTH) -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))


@router.post(
    "/token",
    response_model=KioskTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate temporary kiosk token",
    description="Genera un token temporal para kiosks de SINPE en comercios fisicos.",
)
async def generate_kiosk_token(payload: KioskTokenRequest) -> KioskTokenResponse:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=PAYMENT_WINDOW_MINUTES)

    return KioskTokenResponse(
        token=generate_token(),
        expires_at=expires_at,
        message="Coloque este codigo en el comprobante SINPE.",
        kiosk_id=payload.kiosk_id,
    )
