import json
from typing import Optional, Dict, Any, List
import redis.asyncio as aioredis
from src.backend.adapters.out_bound.cache_gateway import ICacheGateway
from src.backend.infrastructure.cache.lua_scripts import RESERVE_SLOT_LUA, ROLLBACK_SLOT_LUA

class RedisCacheGateway(ICacheGateway):
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._reserve_sha: Optional[str] = None
        self._rollback_sha: Optional[str] = None

    async def _get_reserve_sha(self) -> str:
        if self._reserve_sha is None:
            self._reserve_sha = await self.redis.script_load(RESERVE_SLOT_LUA)
        return self._reserve_sha

    async def _get_rollback_sha(self) -> str:
        if self._rollback_sha is None:
            self._rollback_sha = await self.redis.script_load(ROLLBACK_SLOT_LUA)
        return self._rollback_sha

    async def atomic_reserve_slot(
        self,
        student_id: str,
        section_id: str,
        prerequisite_course_code: str,
        section_time_mask: int,
        credits: int
    ) -> Dict[str, Any]:
        keys = [
            f"section:{section_id}:slots",
            f"section:{section_id}:enrolled",
            f"student:{student_id}:completed_courses",
            f"student:{student_id}:credits",
            f"student:{student_id}:registered_mask"
        ]
        args = [
            student_id,
            prerequisite_course_code or "NONE",
            section_time_mask,
            credits
        ]
        
        try:
            sha = await self._get_reserve_sha()
            code = await self.redis.evalsha(sha, len(keys), *keys, *args)
        except aioredis.ResponseError:
            # Fallback nếu script chưa load trên server
            code = await self.redis.eval(RESERVE_SLOT_LUA, len(keys), *keys, *args)

        code_int = int(code)
        messages = {
            1: "RESERVED",
            -1: "ALREADY_ENROLLED",
            -2: "SECTION_FULL",
            -3: "PREREQUISITE_NOT_MET",
            -4: "CREDIT_LIMIT_EXCEEDED",
            -5: "SCHEDULE_CONFLICT"
        }
        return {"code": code_int, "message": messages.get(code_int, "UNKNOWN_CODE")}

    async def atomic_release_slot(
        self,
        student_id: str,
        section_id: str,
        credits: int,
        section_time_mask: int
    ) -> bool:
        keys = [
            f"section:{section_id}:slots",
            f"section:{section_id}:enrolled",
            f"student:{student_id}:credits",
            f"student:{student_id}:registered_mask"
        ]
        args = [student_id, section_time_mask, credits]
        try:
            sha = await self._get_rollback_sha()
            res = await self.redis.evalsha(sha, len(keys), *keys, *args)
        except aioredis.ResponseError:
            res = await self.redis.eval(ROLLBACK_SLOT_LUA, len(keys), *keys, *args)
        return int(res) == 1

    async def set_ticket_status(self, ticket_id: str, status: str, reason: str = "") -> None:
        key = f"ticket:{ticket_id}:status"
        mapping = {"status": status}
        if reason:
            mapping["reason"] = reason
        await self.redis.hset(key, mapping=mapping)
        await self.redis.expire(key, 1800)  # 30 phút TTL

    async def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, str]]:
        key = f"ticket:{ticket_id}:status"
        data = await self.redis.hgetall(key)
        if not data:
            return None
        return data

    async def get_active_catalog(self) -> Optional[List[Dict[str, Any]]]:
        raw = await self.redis.get("catalog:active_sections")
        if not raw:
            return None
        try:
            catalog = json.loads(raw)
            if isinstance(catalog, list) and catalog:
                slot_keys = [f"section:{sec['id']}:slots" for sec in catalog]
                slots = await self.redis.mget(slot_keys)
                for sec, slot_val in zip(catalog, slots):
                    if slot_val is not None:
                        avail = max(0, int(slot_val))
                        sec["available_slots"] = avail
                        sec["current_enrolled"] = sec["max_capacity"] - avail
            return catalog
        except Exception:
            return None

    async def set_active_catalog(self, sections: List[Dict[str, Any]]) -> None:
        await self.redis.set("catalog:active_sections", json.dumps(sections), ex=43200) # 12 giờ TTL
