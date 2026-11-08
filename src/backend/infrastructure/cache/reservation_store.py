import json
import time
import os
from dataclasses import asdict
from src.backend.core.domain.entities.operation import Operation, RegistrationError

RESERVE = """
local old = redis.call('GET', KEYS[1])
if old then
 local record = cjson.decode(old)
 if record.hash ~= ARGV[2] then return 'IDEMPOTENCY_CONFLICT' end
 return redis.call('GET', ARGV[4] .. 'op:' .. record.ticket)
end
local data = cjson.decode(ARGV[1])
local ctx = data.context
if ctx.run_id ~= cjson.null and ctx.run_id ~= nil then
 local run = redis.call('GET', ARGV[4] .. 'run:' .. ctx.run_id)
 if not run or run ~= tostring(ctx.generation) then return 'STALE_GENERATION' end
end
if redis.call('HEXISTS', KEYS[3], ctx.student_id) == 1 then return 'ALREADY_REGISTERED' end
if tonumber(redis.call('GET', KEYS[2]) or '0') <= 0 then return 'SECTION_FULL' end
local completed = false
for _, code in ipairs(ctx.completed_courses) do
 if code == ctx.prerequisite_course_code then completed = true end
end
if ctx.prerequisite_course_code ~= cjson.null and ctx.prerequisite_course_code ~= nil and not completed then
 return 'PREREQUISITE_NOT_MET'
end
if tonumber(redis.call('GET', KEYS[4]) or '0') + ctx.credits > ctx.max_credits then return 'CREDIT_LIMIT_EXCEEDED' end
for _, slot in ipairs(ctx.time_slots) do
 if redis.call('SISMEMBER', KEYS[5], tostring(slot)) == 1 then return 'SCHEDULE_CONFLICT' end
end
redis.call('DECR', KEYS[2])
redis.call('HSET', KEYS[3], ctx.student_id, data.operation.ticket_id)
redis.call('INCRBY', KEYS[4], ctx.credits)
for _, slot in ipairs(ctx.time_slots) do redis.call('SADD', KEYS[5], tostring(slot)) end
redis.call('SET', KEYS[1], cjson.encode({hash=ARGV[2], ticket=data.operation.ticket_id}))
redis.call('SET', KEYS[6], ARGV[1])
redis.call('ZADD', KEYS[7], ARGV[3], data.operation.ticket_id)
return ARGV[1]
"""

RELEASE = """
if redis.call('HGET', KEYS[2], ARGV[1]) ~= ARGV[2] then return 0 end
redis.call('HDEL', KEYS[2], ARGV[1])
redis.call('INCR', KEYS[1])
redis.call('DECRBY', KEYS[3], ARGV[3])
for _, slot in ipairs(cjson.decode(ARGV[4])) do redis.call('SREM', KEYS[4], tostring(slot)) end
return 1
"""

CREATE_DROP = """
local prior = redis.call('GET', KEYS[1])
if prior then
 local old = cjson.decode(prior)
 if old.hash ~= ARGV[2] then return 'IDEMPOTENCY_CONFLICT' end
 return redis.call('GET', ARGV[4] .. 'op:' .. old.ticket)
end
local data = cjson.decode(ARGV[1])
if redis.call('HGET', KEYS[4], data.context.student_id) ~= data.expected_ticket_id then return 'STALE_OPERATION' end
redis.call('SET', KEYS[1], cjson.encode({hash=ARGV[2], ticket=data.operation.ticket_id}))
redis.call('SET', KEYS[2], ARGV[1])
redis.call('ZADD', KEYS[3], ARGV[3], data.operation.ticket_id)
return ARGV[1]
"""

class ReservationStore:
    def __init__(self, redis, prefix="lab:"):
        self.redis, self.prefix = redis, prefix
        self._reserve = redis.register_script(RESERVE)
        self._release = redis.register_script(RELEASE)
        self._drop = redis.register_script(CREATE_DROP)

    def keys(self, ctx):
        p = self.prefix
        student = f"{p}student:{ctx.semester_id}:{ctx.student_id}"
        return [f"{p}section:{ctx.section_id}:slots", f"{p}section:{ctx.section_id}:owners",
                student + ":credits", student + ":periods"]

    def decode(self, raw):
        if not raw or not raw.startswith("{"):
            raise RegistrationError(raw or "OPERATION_MISSING")
        return Operation(**json.loads(raw)["operation"])

    async def reserve(self, ctx, ticket_id, idempotency_key, payload_hash):
        op = Operation(ticket_id, ctx.student_id, ctx.section_id, "REGISTER", "PENDING", ctx.generation)
        data = {"operation": asdict(op), "context": asdict(ctx), "key": idempotency_key, "hash": payload_hash}
        raw = await self._reserve(keys=[self.prefix+"idem:"+idempotency_key, *self.keys(ctx),
            self.prefix+"op:"+ticket_id, self.prefix+"pending"],
            args=[json.dumps(data), payload_hash, time.time(), self.prefix])
        return self.decode(raw)

    async def create_drop(self, ctx, ticket_id, registration_id, expected_ticket_id, key):
        op = Operation(ticket_id, ctx.student_id, ctx.section_id, "DROP", "CANCEL_PENDING",
                       ctx.generation, registration_id=registration_id)
        data = {"operation": asdict(op), "context": asdict(ctx), "key": key, "hash": registration_id,
                "expected_ticket_id": expected_ticket_id}
        return self.decode(await self._drop(keys=[self.prefix+"idem:"+key, self.prefix+"op:"+ticket_id,
            self.prefix+"pending", self.keys(ctx)[1]],
            args=[json.dumps(data), registration_id, time.time(), self.prefix]))

    async def release(self, ctx, ticket_id):
        return bool(await self._release(keys=self.keys(ctx),
            args=[ctx.student_id, ticket_id, ctx.credits, json.dumps(ctx.time_slots)]))

    async def record(self, ticket_id):
        raw = await self.redis.get(self.prefix+"op:"+ticket_id)
        return json.loads(raw) if raw else None

    async def get_operation(self, ticket_id):
        data = await self.record(ticket_id)
        return Operation(**data["operation"]) if data else None

    async def finish(self, op):
        data = await self.record(op.ticket_id)
        if not data:
            return
        data["operation"] = asdict(op)
        async with self.redis.pipeline(transaction=True) as pipe:
            retention = max(60, int(os.getenv("OPERATION_RETENTION_SECONDS", "604800")))
            pipe.set(self.prefix+"op:"+op.ticket_id, json.dumps(data), ex=retention)
            pipe.expire(self.prefix+"idem:"+data["key"], retention)
            pipe.zrem(self.prefix+"pending", op.ticket_id)
            await pipe.execute()

    async def pending(self, older_than_seconds=0, limit=100):
        return await self.redis.zrangebyscore(self.prefix+"pending", "-inf",
            time.time()-older_than_seconds, start=0, num=limit)
