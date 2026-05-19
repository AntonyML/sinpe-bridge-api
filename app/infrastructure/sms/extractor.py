import re
from datetime import datetime, timezone

from app.domain.payments.schemas import ParsedSinpeData


_AMOUNT_RE = re.compile(
    r"[₡¢]\s*([\d]{1,3}(?:[,.]?\d{3})*(?:[.,]\d{1,2})?)"
)

_PHONE_RE = re.compile(
    r"(?:tel:|telf:|cel:|móvil:)?\s*\+?506[-\s]?(\d{4})[-\s]?(\d{4})"
)

_REFERENCE_RE = re.compile(
    r"(?:ref(?:erencia)?[:\s#]*)(\d{6,20})",
    re.IGNORECASE,
)


_NAME_RE = re.compile(
    r"\bde\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑA-Za-z]+){0,3})",
    re.UNICODE,
)

_DATE_RE = re.compile(
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
)

_TIME_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b"
)


def _clean_amount(raw: str) -> float:
    """Convert '5,000.00' or '5.000,00' to float."""
    cleaned = raw.replace(",", "").replace(".", "")
    if "." in raw and raw.index(".") > raw.rindex(",") if "," in raw else True:
        parts = raw.rsplit(".", 1)
        cleaned = parts[0].replace(",", "") + "." + parts[1]
    elif "," in raw:
        parts = raw.rsplit(",", 1)
        if len(parts[1]) <= 2:
            cleaned = parts[0].replace(".", "") + "." + parts[1]
        else:
            cleaned = raw.replace(",", "")
    else:
        cleaned = raw
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_sinpe_data(sms_body: str) -> ParsedSinpeData:
   
    body = sms_body.strip()

    # cantidad
    amount: float | None = None
    match = _AMOUNT_RE.search(body)
    if match:
        amount = _clean_amount(match.group(1))

    # telefono
    sender_phone: str | None = None
    match = _PHONE_RE.search(body)
    if match:
        sender_phone = match.group(1) + match.group(2)  # 8 digit local number

    # numero de referencia
    reference: str | None = None
    match = _REFERENCE_RE.search(body)
    if match:
        reference = match.group(1)

    # Emisor 
    sender_name: str | None = None
    match = _NAME_RE.search(body)
    if match:
        sender_name = match.group(1).strip()

    # Fecha y hora de la transacción 
    transaction_at: datetime | None = None
    date_match = _DATE_RE.search(body)
    time_match = _TIME_RE.search(body)
    if date_match:
        day, month, year = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        if year < 100:
            year += 2000
        hour = minute = second = 0
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            second = int(time_match.group(3)) if time_match.group(3) else 0
        try:
            transaction_at = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except ValueError:
            transaction_at = None

    #  Banco  
    bank: str | None = None
    for b in ("BCR", "BAC", "BN", "BNCR", "Scotiabank", "Davivienda", "Popular"):
        if b.upper() in body.upper():
            bank = b
            break

    return ParsedSinpeData(
        amount=amount,
        sender_name=sender_name,
        sender_phone=sender_phone,
        reference=reference,
        bank=bank,
        transaction_at=transaction_at,
    )
