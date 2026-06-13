from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class OcrResult:
    """Texto crudo extraído de una imagen más metadata útil."""
    text: str                      # Texto completo reconocido
    confidence: float | None = None  # Confianza promedio (0.0 a 1.0)
    provider: str = ""             # Identificador del proveedor 
    raw: dict = field(default_factory=dict)  # Respuesta cruda


@runtime_checkable
class OCRProvider(Protocol):
    """Cualquier proveedor de OCR debe implementar esto."""

    def is_configured(self) -> bool:
        """True si el proveedor tiene credenciales/endpoint para operar."""
        ...

    async def extract_text(
        self, image_bytes: bytes, content_type: str = "application/octet-stream"
    ) -> OcrResult:
        """Recibe los bytes de una imagen y devuelve el texto reconocido."""
        ...
