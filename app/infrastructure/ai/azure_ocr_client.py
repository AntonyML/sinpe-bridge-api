"""Solo extraemos texto crudo; el parseo a campos estructurados (monto, referencia,
etc.) """

import asyncio
import logging

import httpx

from app.core.config import settings
from app.infrastructure.ai.interfaces import OcrResult

logger = logging.getLogger(__name__)


class AzureOcrError(Exception):
    """Error al conectar a Azure Document Intelligence."""


class AzureDocumentIntelligenceClient:
    """Implementa OCRProvider sobre Azure Document Intelligence."""

    PROVIDER = "azure-di"

    def __init__(
        self,
        endpoint: str | None = None,
        key: str | None = None,
        model: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._endpoint = (endpoint or settings.AZURE_DI_ENDPOINT or "").rstrip("/")
        self._key = key or settings.AZURE_DI_KEY
        self._model = model or settings.AZURE_DI_MODEL
        self._api_version = api_version or settings.AZURE_DI_API_VERSION
        self._timeout = settings.AZURE_DI_TIMEOUT_SECONDS
        self._poll_interval = settings.AZURE_DI_POLL_INTERVAL_SECONDS
        self._max_poll_attempts = settings.AZURE_DI_MAX_POLL_ATTEMPTS

    def is_configured(self) -> bool:
        return bool(self._endpoint and self._key)

    async def extract_text(
        self, image_bytes: bytes, content_type: str = "application/octet-stream"
    ) -> OcrResult:
        if not self.is_configured():
            raise AzureOcrError(
                "Azure Document Intelligence no está configurado "
                "(faltan AZURE_DI_ENDPOINT y/o AZURE_DI_KEY)"
            )

        analyze_url = (
            f"{self._endpoint}/documentintelligence/documentModels/"
            f"{self._model}:analyze"
        )
        params = {"api-version": self._api_version}
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                analyze_url, params=params, headers=headers, content=image_bytes
            )
            if resp.status_code != 202:
                raise AzureOcrError(
                    f"Azure analyze falló: HTTP {resp.status_code} - {resp.text[:500]}"
                )

            operation_location = resp.headers.get("Operation-Location")
            if not operation_location:
                raise AzureOcrError("Azure no devolvió el header Operation-Location")

            result = await self._poll_result(client, operation_location)

        return self._to_ocr_result(result)

    async def _poll_result(
        self, client: httpx.AsyncClient, operation_location: str
    ) -> dict:
        """Hace polling al resultado hasta que termine o se agoten los intentos."""
        headers = {"Ocp-Apim-Subscription-Key": self._key}

        for attempt in range(self._max_poll_attempts):
            await asyncio.sleep(self._poll_interval)
            resp = await client.get(operation_location, headers=headers)
            if resp.status_code != 200:
                raise AzureOcrError(
                    f"Azure poll falló: HTTP {resp.status_code} - {resp.text[:500]}"
                )

            data = resp.json()
            status = (data.get("status") or "").lower()

            if status == "succeeded":
                return data
            if status == "failed":
                error = data.get("error", {})
                raise AzureOcrError(f"Azure reportó análisis fallido: {error}")
            # status "running" / "notStarted" → seguir esperando
            logger.debug("Azure OCR en progreso (intento %s, status=%s)", attempt + 1, status)

        raise AzureOcrError(
            f"Azure OCR no terminó tras {self._max_poll_attempts} intentos "
            f"({self._max_poll_attempts * self._poll_interval:.0f}s)"
        )

    def _to_ocr_result(self, data: dict) -> OcrResult:
        """Convierte la respuesta de Azure en nuestro OcrResult estándar."""
        analyze_result = data.get("analyzeResult", {})
        text = analyze_result.get("content", "") or ""

        # Confianza promedio a nivel de palabra 
        confidences = [
            word["confidence"]
            for page in analyze_result.get("pages", [])
            for word in page.get("words", [])
            if "confidence" in word
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        return OcrResult(
            text=text,
            confidence=avg_confidence,
            provider=self.PROVIDER,
            raw=data,
        )



_ocr_client: AzureDocumentIntelligenceClient | None = None


def get_ocr_client() -> AzureDocumentIntelligenceClient:
    global _ocr_client
    if _ocr_client is None:
        _ocr_client = AzureDocumentIntelligenceClient()
    return _ocr_client
