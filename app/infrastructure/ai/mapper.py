"""El cliente de Azure solo nos da el texto reconocido de la imagen. Para conciliar
necesitamos los mismos campos estructurados que produce el extractor de SMS
(monto, teléfono, referencia, nombre, fecha). En lugar de duplicar esa lógica,
reutilizamos `extract_sinpe_data`, que ya sabe sacar esos campos de texto libre.
"""

from app.domain.payments.schemas import ParsedSinpeData
from app.infrastructure.ai.interfaces import OcrResult
from app.infrastructure.ai.receipt_parser import parse_receipt
from app.infrastructure.sms.extractor import extract_sinpe_data


def map_ocr_to_parsed(ocr: OcrResult) -> ParsedSinpeData:
    """
    Convierte el texto del OCR en datos estructurados para conciliar.
    """
    text = (ocr.text or "").strip()

    parsed = parse_receipt(text)

    # Respaldo: si el parser de comprobante no encontró ni monto ni referencia,
    # probablemente el texto no es un comprobante con etiquetas → usar el de SMS.
    if parsed.amount is None and parsed.reference is None:
        return extract_sinpe_data(text)

    return parsed
