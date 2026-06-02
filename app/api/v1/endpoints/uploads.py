import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from app.api.deps import get_upload_service
from app.core.middleware import get_trace_context
from app.domain.uploads.schemas import ImageType, UploadResponse
from app.domain.uploads.service import UploadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post(
    "/receipts",
    response_model=UploadResponse,
    summary="Upload receipt image",
    description="Upload a receipt/QR image for processing and OCR"
)
async def upload_receipt(
    file: UploadFile = File(...),
    id_pos: str = Form(...),
    correlation_token: str = Form(...),
    device_id: str = Form(...),
    correlation_id: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None),
    upload_service: UploadService = Depends(get_upload_service),
):
    trace_context = get_trace_context()
    
    try:
        # Read file content
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        response = await upload_service.upload_file(
            file_content=content,
            filename=file.filename or "receipt.jpg",
            mime_type=file.content_type or "image/jpeg",
            image_type=ImageType.RECEIPT_QR,
            id_pos=id_pos,
            correlation_token=correlation_token,
            device_id=device_id,
            correlation_id=correlation_id or trace_context.correlation_id,
            message_id=message_id,
        )

        logger.info(
            f"Receipt uploaded: upload_id={response.upload_id}, "
            f"size={response.file_size}, correlation_id={trace_context.correlation_id}"
        )

        return response
        
    except ValueError as e:
        logger.warning(f"Upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.post(
    "/qr",
    response_model=UploadResponse,
    summary="Upload QR code image",
    description="Upload a QR code image for decoding and processing"
)
async def upload_qr(
    file: UploadFile = File(...),
    id_pos: str = Form(...),
    correlation_token: str = Form(...),
    device_id: str = Form(...),
    correlation_id: Optional[str] = Form(None),
    upload_service: UploadService = Depends(get_upload_service),
):
    trace_context = get_trace_context()
    
    try:
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        response = await upload_service.upload_file(
            file_content=content,
            filename=file.filename or "qr.png",
            mime_type=file.content_type or "image/png",
            image_type=ImageType.RECEIPT_QR,
            id_pos=id_pos,
            correlation_token=correlation_token,
            device_id=device_id,
            correlation_id=correlation_id or trace_context.correlation_id,
        )

        logger.info(
            f"QR uploaded: upload_id={response.upload_id}, "
            f"correlation_id={trace_context.correlation_id}"
        )

        return response
        
    except ValueError as e:
        logger.warning(f"QR upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"QR upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get(
    "/{upload_id}",
    response_model=UploadResponse,
    summary="Get upload metadata",
    description="Retrieve metadata for a specific upload"
)
async def get_upload(
    upload_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    trace_context = get_trace_context()
    
    try:
        file_path = await upload_service.get_file_path(upload_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Return basic info (full implementation would query database)
        return {
            "upload_id": upload_id,
            "file_path": str(file_path),
            "correlation_id": trace_context.correlation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve upload")


@router.delete(
    "/{upload_id}",
    status_code=204,
    summary="Delete upload",
    description="Delete an uploaded file"
)
async def delete_upload(
    upload_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    trace_context = get_trace_context()
    
    deleted = await upload_service.delete_file(upload_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    logger.info(f"Upload deleted: {upload_id}, correlation_id={trace_context.correlation_id}")
    return None
