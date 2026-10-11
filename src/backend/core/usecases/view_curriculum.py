from typing import List, Dict, Any, Optional
from src.backend.adapters.out_bound.cache_gateway import ICacheGateway
from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway

class ViewCurriculumUseCase:
    def __init__(
        self,
        cache_gateway: ICacheGateway,
        persistence_gateway: IPersistenceGateway
    ):
        self.cache_gateway = cache_gateway
        self.persistence_gateway = persistence_gateway

    async def execute(self, semester_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # 1. Thử lấy từ cache key catalog:active_sections (< 1ms)
        cached_catalog = await self.cache_gateway.get_active_catalog()
        if cached_catalog is not None:
            return cached_catalog

        # 2. Nếu cache miss (chỉ xảy ra khi chưa warmup): truy vấn DB và ghi cache
        sections = await self.persistence_gateway.get_active_sections(semester_id)
        if sections:
            await self.cache_gateway.set_active_catalog(sections)
        return sections
