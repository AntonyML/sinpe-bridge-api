"""
Upload service for handling image and file uploads in SINPE Bridge API.

Provides:
- Multipart form-data parsing
- File validation (MIME type, size)
- Storage abstraction (local or R2)
- OCR pipeline preparation
"""

import logging
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime
import uuid
import aiofiles

from app.core.config import settings
from app.domain.uploads.schemas import ImageType, UploadResponse

logger = logging.getLogger(__name__)


class UploadService:
    """Service for managing file uploads."""
    
    ALLOWED_MIME_TYPES = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/webp": [".webp"],
        "application/pdf": [".pdf"],
    }
    
    def __init__(self):
        self.max_file_size = settings.MAX_UPLOAD_SIZE
        self.storage_path = Path(settings.UPLOAD_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        image_type: ImageType,
        device_id: str,
        correlation_id: str,
        message_id: Optional[str] = None,
    ) -> UploadResponse:
        """
        Upload a file with validation and storage.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type from Content-Type header
            image_type: Type of image being uploaded
            device_id: Device identifier
            correlation_id: Request correlation ID
            message_id: Related message ID if applicable
            
        Returns:
            UploadResponse with storage location and metadata
            
        Raises:
            ValueError: If file validation fails
        """
        # === VALIDATION ===
        
        # Check file size
        file_size = len(file_content)
        if file_size > self.max_file_size:
            raise ValueError(
                f"File too large: {file_size} > {self.max_file_size} bytes"
            )
        
        # Check MIME type
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(f"MIME type not allowed: {mime_type}")
        
        # Check file extension
        _, ext = os.path.splitext(filename)
        allowed_exts = self.ALLOWED_MIME_TYPES[mime_type]
        if ext.lower() not in allowed_exts:
            raise ValueError(
                f"File extension {ext} not allowed for {mime_type}"
            )
        
        # === STORAGE ===
        
        # Generate secure filename
        upload_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(file_content).hexdigest()
        secure_filename = f"{upload_id}_{file_hash[:8]}{ext}"
        
        # Create directory structure: /uploads/YYYY/MM/DD/device_hash/
        now = datetime.utcnow()
        device_hash = hashlib.sha256(device_id.encode()).hexdigest()[:16]
        
        dir_path = (
            self.storage_path
            / str(now.year)
            / f"{now.month:02d}"
            / f"{now.day:02d}"
            / device_hash
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / secure_filename
        
        # Write file
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_content)
            logger.info(
                f"File uploaded: {secure_filename}, size={file_size}, "
                f"hash={file_hash}, device_hash={device_hash}"
            )
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            raise ValueError(f"Storage error: {e}")
        
        # === RESPONSE ===
        
        return UploadResponse(
            upload_id=upload_id,
            file_path=str(file_path.relative_to(self.storage_path)),
            file_size=file_size,
            mime_type=mime_type,
            image_type=image_type,
            correlation_id=correlation_id,
            message_id=message_id,
            created_at=datetime.utcnow(),
        )
    
    async def get_file_path(self, upload_id: str) -> Optional[Path]:
        """
        Retrieve file path for a stored upload.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            Path to file or None if not found
        """
        # Search for file in storage
        for root, dirs, files in os.walk(self.storage_path):
            for file in files:
                if file.startswith(upload_id):
                    return Path(root) / file
        return None
    
    async def delete_file(self, upload_id: str) -> bool:
        """
        Delete a stored upload.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            True if deleted, False if not found
        """
        file_path = await self.get_file_path(upload_id)
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"File deleted: {upload_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete file: {e}")
                return False
        return False
    
    def compute_file_hash(self, file_content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()


# Singleton instance
_upload_service: Optional[UploadService] = None


def get_upload_service() -> UploadService:
    """Get or create upload service instance."""
    global _upload_service
    if _upload_service is None:
        _upload_service = UploadService()
    return _upload_service
