from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.models import SinpeImageReceipt


class UploadRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_receipt(
        self,
        correlation_session_id,
        id_pos: str,
        image_url: str,
        image_storage_path: str,
        image_hash: str,
        mime_type: str,
        image_size_bytes: int,
        device_id: str,
        extracted_token: str,
        device_metadata: dict | None = None,
    ) -> SinpeImageReceipt:
        receipt = SinpeImageReceipt(
            correlation_session_id=correlation_session_id,
            id_pos=id_pos,
            image_url=image_url,
            image_storage_path=image_storage_path,
            image_hash=image_hash,
            mime_type=mime_type,
            image_size_bytes=image_size_bytes,
            device_id=device_id,
            extracted_token=extracted_token,
            device_metadata=device_metadata or {},
        )
        self._db.add(receipt)
        await self._db.commit()
        await self._db.refresh(receipt)
        return receipt