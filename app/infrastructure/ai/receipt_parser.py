"""
Parser de comprobantes SINPE en imagen (formato de bancos de Costa Rica).
"""

import re
from datetime import datetime, timezone

from app.domain.payments.schemas import ParsedSinpeData

# Meses en español → número (para fechas tipo "02 de junio, 2026")
_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_BANCOS = ("BCR", "BAC", "BNCR", "BN", "Scotiabank", "Davivienda", "Popular", "Lafise", "Promerica")


def _parse_cr_amount(raw: str) -> float | None:
    """Convierte '2.500,00' (formato CR) a 2500.00."""
    raw = raw.strip()
    if "," in raw:
        # coma = decimales, punto = miles
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _find_amount(text: str) -> float | None:
    """
    Prioriza 'Monto transferido' (lo que efectivamente recibe el comercio),
    luego 'Monto debitado', y como último recurso el primer monto con ₡.
    """
    patterns = [
        r"Monto\s+transferido[\s\S]{0,40}?[₡¢]\s*([\d.,]+)",
        r"Monto\s+debitado[\s\S]{0,40}?[₡¢]\s*([\d.,]+)",
        r"[₡¢]\s*([\d.,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            amount = _parse_cr_amount(m.group(1))
            if amount is not None:
                return amount
    return None


def _find_reference(text: str) -> str | None:
    """Número de referencia completo (puede tener más de 20 dígitos)."""
    m = re.search(r"Referencia[\s:#]*([0-9]{6,40})", text, re.IGNORECASE)
    return m.group(1) if m else None


def _find_phone(text: str) -> str | None:
    """
    Teléfono SINPE Móvil del destino (8 dígitos, formato 8670-8452).
    En estos comprobantes el origen es una cuenta, no un teléfono; el único
    teléfono presente suele ser el del destinatario.
    """
    m = re.search(
        r"SINPE\s+M[oó]vil\s+destino[\s\S]{0,60}?(\d{4})[-\s]?(\d{4})",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1) + m.group(2)
    # Respaldo: teléfono con prefijo +506
    m = re.search(r"\+?506[-\s]?(\d{4})[-\s]?(\d{4})", text)
    if m:
        return m.group(1) + m.group(2)
    return None


# Palabras que NO son parte del nombre (etiqueta y prefijos de cuenta).
_NAME_SKIP = {"AH", "CR", "CUENTA", "ORIGEN"}


def _find_name(text: str) -> str | None:
    """
    Nombre del pagador (bajo 'Cuenta origen'). Azure a veces parte la etiqueta
    ('Cuenta' en una línea, 'origen' en otra) y a veces deja el nombre en la
    misma línea de la cuenta. Por eso anclamos en 'Cuenta' y, en esa línea y las
    siguientes, descartamos tokens con dígitos (número de cuenta) y las palabras
    de la etiqueta, quedándonos con la secuencia de nombres en MAYÚSCULAS.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not re.search(r"cuenta", line, re.IGNORECASE):
            continue
        for candidate in lines[i:i + 4]:
            tokens = [
                t for t in candidate.split()
                if not any(c.isdigit() for c in t) and t.upper() not in _NAME_SKIP
            ]
            name = " ".join(tokens)
            if re.fullmatch(r"[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,4}", name):
                return name
        break
    return None


def _find_datetime(text: str) -> datetime | None:
    """Fecha tipo '02 de junio, 2026' + hora '10:21'."""
    date_m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+),?\s+(\d{4})", text, re.IGNORECASE)
    if not date_m:
        return None
    day = int(date_m.group(1))
    month = _MESES.get(date_m.group(2).lower())
    year = int(date_m.group(3))
    if not month:
        return None
    hour = minute = 0
    time_m = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if time_m:
        hour, minute = int(time_m.group(1)), int(time_m.group(2))
    try:
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except ValueError:
        return None


def _find_bank(text: str) -> str | None:
    upper = text.upper()
    for bank in _BANCOS:
        if bank.upper() in upper:
            return bank
    return None


def parse_receipt(text: str) -> ParsedSinpeData:
    """Extrae los campos estructurados de un comprobante SINPE en imagen."""
    return ParsedSinpeData(
        amount=_find_amount(text),
        sender_name=_find_name(text),
        sender_phone=_find_phone(text),
        reference=_find_reference(text),
        bank=_find_bank(text),
        transaction_at=_find_datetime(text),
    )
