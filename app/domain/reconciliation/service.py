import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.repository import OrderRepository
from app.domain.payments.repository import SinpeMessageRepository
from app.domain.payments.schemas import ParsedSinpeData, SinpeIncomingResponse, SinpeMessageIncoming
from app.domain.reconciliation.rules import ReconciliationEngine
from app.infrastructure.db.models import PurchaseOrder as PurchaseOrderModel
from app.infrastructure.sms.extractor import extract_sinpe_data
from app.shared.enums import OrderStatus, ReconciliationResult


class ReconciliationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._order_repo = OrderRepository(db)
        self._msg_repo = SinpeMessageRepository(db)
        self._engine = ReconciliationEngine()

    async def process_incoming_message(
        self, incoming: SinpeMessageIncoming
    ) -> SinpeIncomingResponse:

        message_id = uuid.UUID(incoming.envelope.message_id)

        # 1. Verificar si el mensaje ya fue recibido antes
        # Si la app móvil reintenta el envío, no lo procesamos dos veces
        existing = await self._msg_repo.get_by_message_id(message_id)
        if existing:
            return SinpeIncomingResponse(
                message_id=message_id,
                processed=existing.processed,
                reconciliation_result=None,
                order_number=None,
                detail="Mensaje ya recibido anteriormente (message_id duplicado)",
            )

        # 2. Convertir el timestamp a datetime 
        sms_timestamp: datetime | None = None
        if incoming.payload.timestamp:
            sms_timestamp = datetime.fromtimestamp(
                incoming.payload.timestamp, tz=timezone.utc
            )

        # 3. Guardar el mensaje en la base de datos antes de procesarlo
        raw_msg = await self._msg_repo.create(
            id_pos=incoming.id_pos,
            message_id=message_id,
            body=incoming.payload.body,
            sender=incoming.payload.sender,
            message_timestamp=sms_timestamp,
            envelope=incoming.envelope.model_dump(),
            payload_raw=incoming.payload.model_dump(),
        )

        # 4. Extraer los datos estructurado(monto, teléfono, referencia, nombre, fecha)
        parsed: ParsedSinpeData = extract_sinpe_data(incoming.payload.body)

        # 5. Buscar la orden pendiente que corresponde a este pago
        order: PurchaseOrderModel | None = None

        # buscar por teléfono del que paga (correlation_token)
        if parsed.sender_phone:
            order = await self._order_repo.find_pending_by_token(
                incoming.id_pos, parsed.sender_phone
            )

        #  si no se encontró por teléfono, buscar solo por monto
        if order is None and parsed.amount is not None:
            order = await self._order_repo.find_pending_by_amount(
                incoming.id_pos, parsed.amount
            )

        # Si no se encontró ninguna orden que coincida, terminar aquí
        if order is None:
            await self._msg_repo.mark_processed(raw_msg.id, None)
            return SinpeIncomingResponse(
                message_id=message_id,
                processed=True,
                reconciliation_result=ReconciliationResult.NO_ORDER_FOUND,
                order_number=None,
                detail="No se encontró ninguna orden pendiente que coincida con este pago",
            )

        # 6. Verificar que la referencia SINPE no haya sido usada antes
        reference_used = False
        if parsed.reference:
            reference_used = await self._msg_repo.reference_exists(parsed.reference)

        # 7. Ejecutar las reglas de conciliación y obtener el resultado
        result, detail = self._engine.evaluate(order, parsed, reference_used)

        # 8. Actualizar el estado de la orden según el resultado
        new_status: OrderStatus | None = None
        if result == ReconciliationResult.APPROVED:
            new_status = OrderStatus.CONFIRMED     # confirmado
        elif result == ReconciliationResult.UNDER_REVIEW:
            new_status = OrderStatus.REVIEW        #  revisión manual
        elif result == ReconciliationResult.EXPIRED:
            new_status = OrderStatus.EXPIRED       # pago llegó fuera de tiempo
        #La orden sigue PENDING para reintento

        if new_status:
            await self._order_repo.update_status(order.id, new_status)

        # 9. Marcar el mensaje como procesado y enlazarlo con la orden encontrada
        await self._msg_repo.mark_processed(
            raw_msg.id,
            order.id if result != ReconciliationResult.DUPLICATE else None,
            parsed.reference,
        )

        return SinpeIncomingResponse(
            message_id=message_id,
            processed=True,
            reconciliation_result=result,
            order_number=order.order_number,
            detail=detail,
        )