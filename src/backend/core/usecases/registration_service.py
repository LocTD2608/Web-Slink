import hashlib
import uuid
from src.backend.core.domain.entities.registration_context import RegistrationContext
from src.backend.core.domain.entities.operation import Operation, RegistrationError


def intent_key(student_id, kind, key):
    if not key or len(key) > 128:
        raise RegistrationError("IDEMPOTENCY_KEY_REQUIRED", 400)
    return hashlib.sha256(f"{student_id}:{kind}:{key}".encode()).hexdigest()


class RegistrationService:
    def __init__(self, contexts, repository, store, queue, mode):
        self.contexts, self.repository, self.store, self.queue, self.mode = contexts, repository, store, queue, mode

    async def register(self, student_id, section_id, key):
        scoped = intent_key(student_id, "REGISTER", key)
        payload_hash = hashlib.sha256(section_id.encode()).hexdigest()
        if self.mode == "postgres":
            old = await self.repository.get_by_key(scoped, payload_hash)
            if old:
                return old
        ctx = await self.contexts.load_registration_context(student_id, section_id)
        ticket = str(uuid.uuid4())
        if self.mode == "postgres":
            return await self.repository.confirm_registration(ctx, ticket, scoped, payload_hash)
        op = await self.store.reserve(ctx, ticket, scoped, payload_hash)
        if op.status == "PENDING":
            try:
                await self.queue.publish("registration_queue", {"ticket_id": op.ticket_id})
            except Exception as exc:
                exc.ticket_id = op.ticket_id
                raise
        return op

    async def drop(self, registration_id, student_id, key):
        scoped = intent_key(student_id, "DROP", key)
        if self.mode == "postgres":
            old = await self.repository.get_by_key(scoped, registration_id)
            if old:
                return old
        else:
            raw = await self.store.redis.get(self.store.prefix+"idem:"+scoped)
            if raw:
                import json
                data = json.loads(raw)
                if data["hash"] != registration_id:
                    raise RegistrationError("IDEMPOTENCY_CONFLICT")
                return await self.store.get_operation(data["ticket"])
        reg = await self.repository.registration_for_drop(registration_id, student_id)
        ctx = await self.contexts.load_registration_context(student_id, reg["section_id"])
        ticket = str(uuid.uuid4())
        if self.mode == "postgres":
            return await self.repository.cancel_registration(registration_id, student_id, reg["ticket_id"], ticket, scoped)
        op = await self.store.create_drop(ctx, ticket, registration_id, reg["ticket_id"], scoped)
        try:
            await self.queue.publish("drop_queue", {"ticket_id": op.ticket_id})
        except Exception as exc:
            exc.ticket_id = op.ticket_id
            raise
        return op

    async def status(self, ticket_id, student_id):
        op = await self.store.get_operation(ticket_id) if self.mode == "redis_queue" else None
        op = op or await self.repository.get_operation(ticket_id)
        if not op:
            raise RegistrationError("NOT_FOUND", 404)
        if op.student_id != student_id:
            raise RegistrationError("FORBIDDEN", 403)
        return op

    async def process(self, ticket_id):
        data = await self.store.record(ticket_id)
        if not data:
            return
        ctx = RegistrationContext(**data["context"])
        pending = Operation(**data["operation"])
        if pending.status not in ("PENDING", "CANCEL_PENDING"):
            return pending
        if pending.kind == "REGISTER":
            try:
                op = await self.repository.confirm_registration(ctx, ticket_id, data["key"], data["hash"])
            except RegistrationError as exc:
                op = await self.repository.fail_registration(ctx, ticket_id, data["key"], data["hash"], exc.code)
            if op.status == "FAILED":
                await self.store.release(ctx, ticket_id)
            await self.store.finish(op)
        else:
            op = await self.repository.cancel_registration(pending.registration_id, pending.student_id,
                data["expected_ticket_id"], ticket_id, data["key"])
            if op.status == "CANCELLED":
                await self.store.release(ctx, data["expected_ticket_id"])
                old = await self.repository.get_operation(data["expected_ticket_id"])
                if old:
                    await self.store.finish(old)
            await self.store.finish(op)
        return op

    async def recover_pending(self, older_than_seconds=10, limit=100):
        tickets = await self.store.pending(older_than_seconds, limit)
        recovered, deferred = 0, 0
        for ticket in tickets:
            try:
                await self.process(ticket)
                recovered += 1
            except Exception:
                deferred += 1
        return {"recovered": recovered, "deferred": deferred}
