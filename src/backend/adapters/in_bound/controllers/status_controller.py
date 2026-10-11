from fastapi import APIRouter, HTTPException, status
from typing import Optional, Dict, Any
from src.backend.adapters.out_bound.cache_gateway import ICacheGateway

router = APIRouter(prefix="/api/v1/registrations", tags=["Registration Status"])

_cache_gateway: Optional[ICacheGateway] = None

def set_status_cache_gateway(cache_gw: ICacheGateway):
    global _cache_gateway
    _cache_gateway = cache_gw

def get_cache_gateway() -> ICacheGateway:
    assert _cache_gateway is not None, "CacheGateway not initialized"
    return _cache_gateway

@router.get("/status/{ticket_id}")
async def get_registration_status(ticket_id: str):
    """
    Controlled Short Polling Endpoint:
    Đọc trực tiếp trạng thái vé từ Redis key 'ticket:{ticket_id}:status' (< 1ms).
    Trả về trạng thái: PENDING, CONFIRMED, hoặc FAILED kèm thông tin lỗi.
    """
    cache_gw = get_cache_gateway()
    status_data = await cache_gw.get_ticket_status(ticket_id)
    
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vé đăng ký có mã {ticket_id}"
        )

    return {
        "ticket_id": ticket_id,
        "status": status_data.get("status", "PENDING"),
        "reason": status_data.get("reason", "")
    }
