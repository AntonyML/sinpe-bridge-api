"""
Orquestador del flujo de comprobante en imagen.

Une todas las piezas, reutilizando el mismo motor que ya concilia los SMS:

    imagen → (guarda + hash) → Azure OCR → mapper → ParsedSinpeData
           → busca la orden pendiente → ReconciliationEngine.evaluate()
           → actualiza la orden → guarda SinpeImageReceipt → devuelve veredicto

El motor de reglas (ReconciliationEngine) no cambia: recibe el mismo
ParsedSinpeData sin importar si vino de un SMS o de un OCR.

El almacenamiento de la imagen es propio de este flujo (no usa el UploadService
basado en token), para mantener el pipeline OCR independiente.
"""

import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.orders.repository import OrderRepository
from app.domain.payments.repository import SinpeMessageRepository
from app.domain.reconciliation.rules import ReconciliationEngine
from app.domain.uploads.repository import ImageReceiptRepository
from app.domain.uploads.schemas import ImageReconciliationResponse
from app.infrastructure.ai.azure_ocr_client import AzureOcrError, get_ocr_client
from app.infrastructure.ai.mapper import map_ocr_to_parsed
from app.shared.enums import OrderStatus, ReconciliationResult

logger = logging.getLogger(__name__)

_EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


class SinpeImageAnalyzer:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._orders = OrderRepository(db)
        self._messages = SinpeMessageRepository(db)
        self._receipts = ImageReceiptRepository(db)
        self._engine = ReconciliationEngine()
        self._ocr = get_ocr_client()
        self._storage_path = Path(settings.UPLOAD_STORAGE_PATH)

    async def _store_image(self, file_content: bytes, mime_type: str) -> str:
        """
        Guarda la imagen en disco (best-effort) y devuelve un upload_id.

        Si el guardado falla no bloquea el análisis: el texto OCR y la metadata
        igual quedan persistidos en la base.
        """
        upload_id = str(uuid.uuid4())
        ext = _EXT_BY_MIME.get(mime_type, ".bin")
        try:
            now = datetime.utcnow()
            dir_path = self._storage_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
            dir_path.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(dir_path / f"{upload_id}{ext}", "wb") as f:
                await f.write(file_content)
        except Exception as exc:  # noqa: BLE001 - el guardado es best-effort
            logger.warning("No se pudo guardar la imagen en disco: %s", exc)
        return upload_id

    async def analyze(
        self,
        *,
        file_content: bytes,
        filename: str,
        mime_type: str,
        id_pos: str,
        device_id: str,
        correlation_id: str,
        message_id: str | None = None,
    ) -> ImageReconciliationResponse:

        # 1. Calcular el hash y guardar la imagen (almacenamiento propio del flujo OCR)
        file_hash = hashlib.sha256(file_content).hexdigest()
        upload_id = await self._store_image(file_content, mime_type)

        # 2. Anti-duplicado: misma imagen subida dos veces
        if await self._receipts.hash_exists(file_hash):
            return ImageReconciliationResponse(
                upload_id=upload_id,
                reconciliation_result=ReconciliationResult.DUPLICATE.value,
                detail="Esta imagen ya fue procesada anteriormente.",
            )

        # 3. OCR con Azure
        try:
            ocr = await self._ocr.extract_text(file_content, mime_type)
            logger.info(
                "OCR ok (provider=%s, confidence=%.4f, upload_id=%s):\n%s",
                ocr.provider,
                ocr.confidence if ocr.confidence is not None else -1.0,
                upload_id,
                ocr.text,
            )
        except AzureOcrError as exc:
            logger.error("OCR falló: %s", exc)
            receipt = await self._receipts.create(
                id_pos=id_pos,
                upload_id=upload_id,
                file_hash=file_hash,
                reconciliation_result=ReconciliationResult.UNDER_REVIEW.value,
                detail=f"OCR no disponible: {exc}",
            )
            return ImageReconciliationResponse(
                upload_id=upload_id,
                receipt_id=str(receipt.id),
                reconciliation_result=ReconciliationResult.UNDER_REVIEW.value,
                detail=f"No se pudo leer la imagen (OCR): {exc}",
            )

        # 4. Mapear el texto OCR a campos estructurados
        parsed = map_ocr_to_parsed(ocr)

        # 5. Buscar la orden pendiente que corresponde a este pago
        order = None
        if parsed.sender_phone:
            order = await self._orders.find_pending_by_token(id_pos, parsed.sender_phone)
        if order is None and parsed.amount is not None:
            order = await self._orders.find_pending_by_amount(id_pos, parsed.amount)

        # Base de la respuesta con todo lo extraído (se completa con el veredicto)
        base = dict(
            upload_id=upload_id,
            ocr_confidence=ocr.confidence,
            amount=parsed.amount,
            sender_name=parsed.sender_name,
            sender_phone=parsed.sender_phone,
            reference=parsed.reference,
            bank=parsed.bank,
            transaction_at=parsed.transaction_at,
        )

        if order is None:
            receipt = await self._persist(
                id_pos, upload_id, file_hash, ocr, parsed,
                ReconciliationResult.NO_ORDER_FOUND,
                "No se encontró ninguna orden pendiente que coincida.",
                None,
            )
            return ImageReconciliationResponse(
                **base,
                receipt_id=str(receipt.id),
                reconciliation_result=ReconciliationResult.NO_ORDER_FOUND.value,
                detail="No se encontró ninguna orden pendiente que coincida.",
            )

        # 6. ¿La referencia ya se usó? (chequeo cruzado: SMS + imágenes)
        reference_used = False
        if parsed.reference:
            reference_used = (
                await self._messages.reference_exists(parsed.reference)
                or await self._receipts.reference_exists(parsed.reference)
            )

        # 7. Ejecutar el motor de reglas (idéntico al de SMS)
        result, detail = self._engine.evaluate(order, parsed, reference_used)

        # 8. Salvaguarda por baja confianza del OCR: si el OCR no está seguro,
        #    no aprobamos automáticamente; mandamos a revisión manual.
        if (
            result == ReconciliationResult.APPROVED
            and ocr.confidence is not None
            and ocr.confidence < settings.OCR_MIN_CONFIDENCE
        ):
            result = ReconciliationResult.UNDER_REVIEW
            detail = (
                f"Confianza de OCR baja ({ocr.confidence:.2f} < "
                f"{settings.OCR_MIN_CONFIDENCE}); requiere revisión manual."
            )

        # 9. Actualizar el estado de la orden según el resultado
        new_status: OrderStatus | None = None
        if result == ReconciliationResult.APPROVED:
            new_status = OrderStatus.CONFIRMED
        elif result == ReconciliationResult.UNDER_REVIEW:
            new_status = OrderStatus.REVIEW
        elif result == ReconciliationResult.EXPIRED:
            new_status = OrderStatus.EXPIRED
        if new_status:
            await self._orders.update_status(order.id, new_status)

        # 10. Persistir el comprobante con su veredicto
        linked_order = order.id if result != ReconciliationResult.DUPLICATE else None
        receipt = await self._persist(
            id_pos, upload_id, file_hash, ocr, parsed,
            result, detail, linked_order,
        )

        return ImageReconciliationResponse(
            **base,
            receipt_id=str(receipt.id),
            reconciliation_result=result.value,
            order_number=order.order_number,
            detail=detail,
        )

    async def _persist(
        self, id_pos, upload_id, file_hash, ocr, parsed, result, detail, order_id
    ):
        return await self._receipts.create(
            id_pos=id_pos,
            upload_id=upload_id,
            file_hash=file_hash,
            ocr_provider=ocr.provider,
            ocr_text=ocr.text,
            ocr_confidence=ocr.confidence,
            amount=parsed.amount,
            sender_name=parsed.sender_name,
            sender_phone=parsed.sender_phone,
            reference=parsed.reference,
            bank=parsed.bank,
            transaction_at=parsed.transaction_at,
            reconciliation_result=result.value,
            detail=detail,
            purchase_order_id=order_id,
        )
