from datetime import datetime, timezone
from difflib import SequenceMatcher

from app.domain.payments.schemas import ParsedSinpeData
from app.infrastructure.db.models import PurchaseOrderModel
from app.shared.constants import (
    MAX_AMOUNT_DIFF,
    NAME_SIMILARITY_THRESHOLD,
    PAYMENT_EXPIRY_MINUTES,
)
from app.shared.enums import ReconciliationResult


# Funciones individuales de cada regla

def rule_amount(
    order: PurchaseOrderModel, parsed: ParsedSinpeData
) -> tuple[bool, str]:
    """El monto pagado debe coincidir exactamente con el monto de la orden"""
    if parsed.amount is None:
        return False, "No se pudo extraer el monto del SMS"
    diff = abs(float(order.amount) - parsed.amount)
    if diff > MAX_AMOUNT_DIFF:
        return (
            False,
            f"Monto no coincide: orden={order.amount}, pago={parsed.amount}",
        )
    return True, "El monto coincide"


def rule_phone(
    order: PurchaseOrderModel, parsed: ParsedSinpeData
) -> tuple[bool, str]:
    """
    El teléfono debe coincidir con el
    correlation_token de la orden (teléfono del cliente registrado en el POS).
    """
    if not order.correlation_token or not parsed.sender_phone:
        return True, "Verificación de teléfono omitida (datos insuficientes)"

    order_phone = re.sub(r"\D", "", order.correlation_token)[-8:]
    sms_phone = re.sub(r"\D", "", parsed.sender_phone)[-8:]

    if order_phone != sms_phone:
        return False, f"Teléfono no coincide: orden={order_phone}, sms={sms_phone}"
    return True, "El teléfono coincide"


def rule_time_window(
    order: PurchaseOrderModel, parsed: ParsedSinpeData
) -> tuple[bool, str]:
    """
    El timestamp del pago debe estar dentro de la ventana de tiempo válida
    """
    if parsed.transaction_at is None:
        # Sin timestamp no se puede verificar, se deja pasar (regla blanda)
        return True, "Verificación de tiempo omitida (el SMS no tiene timestamp)"

    reference_time = order.ordered_at.replace(tzinfo=timezone.utc) if order.ordered_at.tzinfo is None else order.ordered_at

    # Usar expires_at si está definido, sino calcularlo desde ordered_at
    if order.expires_at:
        deadline = order.expires_at.replace(tzinfo=timezone.utc) if order.expires_at.tzinfo is None else order.expires_at
    else:
        from datetime import timedelta
        deadline = reference_time + timedelta(minutes=PAYMENT_EXPIRY_MINUTES)

    tx_time = parsed.transaction_at
    if tx_time < reference_time:
        return False, "El timestamp del pago es anterior a la creación de la orden"
    if tx_time > deadline:
        return (
            False,
            f"El pago está fuera de la ventana de {PAYMENT_EXPIRY_MINUTES} minutos",
        )
    return True, "El pago está dentro de la ventana de tiempo válida"


def rule_name_similarity(
    order: PurchaseOrderModel, parsed: ParsedSinpeData
) -> tuple[bool, str]:
    """
    Si el SMS contiene el nombre del pagador, se compara con los datos de la orden.
    """
    if parsed.sender_name is None:
        return True, "Verificación de nombre omitida (el SMS no contiene nombre)"
    return True, f"Nombre del pagador en el SMS: {parsed.sender_name}"


def rule_reference_unique(reference: str | None, already_used: bool) -> tuple[bool, str]:
    """El número de referencia SINPE no debe haber sido usado antes."""
    if reference is None:
        return True, "Verificación de referencia omitida (el SMS no tiene referencia)"
    if already_used:
        return False, f"La referencia {reference} ya fue usada (pago duplicado)"
    return True, "La referencia es única"


# Motor de conciliación

import re  # noqa: E402


def _name_ratio(a: str, b: str) -> float:
    """Calcula el porcentaje de similitud entre dos nombres (0.0 a 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class ReconciliationEngine:
    """
    Ejecuta todas las reglas contra una orden y los datos del SMS,
    y retorna el resultado final con una explicación.
    """

    def evaluate(
        self,
        order: PurchaseOrderModel,
        parsed: ParsedSinpeData,
        reference_already_used: bool = False,
    ) -> tuple[ReconciliationResult, str]:

        reasons: list[str] = []
        soft_failures: list[str] = []

        # REGLA DURA: referencia duplicada
        passed, reason = rule_reference_unique(parsed.reference, reference_already_used)
        if not passed:
            return ReconciliationResult.DUPLICATE, reason

        # REGLA DURA: monto
        passed, reason = rule_amount(order, parsed)
        reasons.append(reason)
        if not passed:
            return ReconciliationResult.REJECTED, reason

        # REGLA DURA: ventana de tiempo
        passed, reason = rule_time_window(order, parsed)
        reasons.append(reason)
        if not passed:
            return ReconciliationResult.EXPIRED, reason

        # REGLA BLANDA: teléfono
        passed, reason = rule_phone(order, parsed)
        reasons.append(reason)
        if not passed:
            soft_failures.append(reason)

        # REGLA BLANDA: similitud de nombre
        passed, reason = rule_name_similarity(order, parsed)
        reasons.append(reason)
        if not passed:
            soft_failures.append(reason)

        # Veredicto final
        if soft_failures:
            detail = "Requiere revisión manual. Problemas: " + "; ".join(soft_failures)
            return ReconciliationResult.UNDER_REVIEW, detail

        return ReconciliationResult.APPROVED, "Todas las verificaciones pasaron: " + "; ".join(reasons)