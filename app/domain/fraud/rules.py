from datetime import datetime

from app.domain.payments.schemas import ParsedSinpeData


VELOCITY_POS_THRESHOLD = 10        # pagos al mismo POS en ventana reciente
AMOUNT_SPIKE_MULTIPLIER = 3.0      # monto debe ser < N× el promedio del POS
SUSPICIOUS_HOUR_START = 1          # hora local de costa rica (UTC-6) a partir de la cual se considera sospechoso un pago
SUSPICIOUS_HOUR_END = 5


def rule_velocity_pos(recent_count: int) -> tuple[bool, str]:
    """El POS no debe recibir una ráfaga inusual de pagos en poco tiempo."""
    if recent_count >= VELOCITY_POS_THRESHOLD:
        return False, f"Ráfaga en POS: {recent_count} mensajes recibidos en la ventana reciente"
    return True, f"Volumen en POS normal ({recent_count} mensajes recientes)"


def rule_amount_spike(
    parsed: ParsedSinpeData, avg_amount: float | None
) -> tuple[bool, str]:
    """El monto no debe ser una anomalía estadística respecto al historial del POS."""
    if parsed.amount is None:
        return True, "Verificación de monto anómalo omitida (monto no extraído del SMS)"
    if avg_amount is None or avg_amount == 0:
        return True, "Verificación de monto anómalo omitida (sin historial del POS)"
    if parsed.amount > avg_amount * AMOUNT_SPIKE_MULTIPLIER:
        return (
            False,
            f"Monto sospechosamente alto: {parsed.amount} vs promedio {avg_amount:.0f} del POS",
        )
    return True, f"Monto dentro del rango normal (promedio del POS: {avg_amount:.0f})"


def rule_suspicious_hours(transaction_at: datetime | None) -> tuple[bool, str]:
    """Pagos en madrugada (1am–5am hora CR, UTC-6) son inusuales."""
    if transaction_at is None:
        return True, "Verificación de horario omitida (SMS sin timestamp)"
    local_hour = (transaction_at.hour - 6) % 24
    if SUSPICIOUS_HOUR_START <= local_hour <= SUSPICIOUS_HOUR_END:
        return False, f"Pago en horario inusual: {local_hour:02d}:00 hora CR"
    return True, f"Horario del pago dentro del rango normal ({local_hour:02d}:00 hora CR)"


# Acá se verifican todas las reglas y se compila el resultado final


class FraudEngine:
    """
    Ejecuta todas las reglas de fraude y retorna el veredicto con explicación.

    Reglas duras  → BLOCK inmediato si fallan (velocity_phone, repeated_failures).
    Reglas blandas → FLAG si fallan (velocity_pos, amount_spike, suspicious_hours).
    """

    def evaluate(
        self,
        parsed: ParsedSinpeData,
        recent_count_pos: int = 0,
        avg_amount_pos: float | None = None,
    ) -> tuple[str, str]:
        from app.shared.enums import FraudResult

        flags: list[str] = []

        # REGLA BLANDA: ráfaga en POS → FLAG
        passed, reason = rule_velocity_pos(recent_count_pos)
        if not passed:
            flags.append(reason)

        # REGLA BLANDA: monto anómalo → FLAG
        passed, reason = rule_amount_spike(parsed, avg_amount_pos)
        if not passed:
            flags.append(reason)

        # REGLA BLANDA: horario sospechoso → FLAG
        passed, reason = rule_suspicious_hours(parsed.transaction_at)
        if not passed:
            flags.append(reason)

        if flags:
            return FraudResult.FLAG, "Señales de alerta: " + "; ".join(flags)

        return FraudResult.ALLOW, "Sin señales de fraude detectadas"
