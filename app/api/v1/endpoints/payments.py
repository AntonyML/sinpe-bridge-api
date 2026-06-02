
import uuid
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_sinpe_message_service
from app.domain.payments.schemas import SinpeMessageCreate, SinpeMessageResponse
from app.domain.payments.service import SinpeMessageService

router = APIRouter()

@router.post(
    "",
    response_model=SinpeMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="La app móvil envía un mensaje SINPE detectado",
)
async def receive_sinpe_message(
    payload: SinpeMessageCreate,
    service: SinpeMessageService = Depends(get_sinpe_message_service),
) -> SinpeMessageResponse:
    return await service.receive(payload)


@router.get(
    "/{message_id}",
    response_model=SinpeMessageResponse,
    summary="Consultar un mensaje por su message_id",
)
async def get_sinpe_message(
    message_id: uuid.UUID,
    service: SinpeMessageService = Depends(get_sinpe_message_service),
) -> SinpeMessageResponse:
    return await service.get_by_message_id(message_id)


@router.get(
    "",
    response_model=list[SinpeMessageResponse],
    summary="Listar todos los mensajes recibidos de un POS",
)
async def list_sinpe_messages(
    id_pos: str = Query(..., description="Identificador del POS"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: SinpeMessageService = Depends(get_sinpe_message_service),
) -> list[SinpeMessageResponse]:
    return await service.list_by_pos(id_pos, limit=limit, offset=offset)
