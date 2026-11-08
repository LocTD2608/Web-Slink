import asyncio, json, logging, time
from prometheus_client import start_http_server
from src.backend.infrastructure.bootstrap import build_service
from src.backend.infrastructure.observability.metrics import Metrics

log = logging.getLogger(__name__)

async def run_worker():
    service, _ = build_service()
    metrics = Metrics()
    server, _ = start_http_server(9101, registry=metrics.registry)
    channel = await service.queue.get_channel()
    await channel.set_qos(prefetch_count=20)
    async def consume(message):
        async with message.process(requeue=False):
            started = time.perf_counter()
            kind = message.routing_key
            try:
                ticket = json.loads(message.body)["ticket_id"]
                for attempt in range(3):
                    try:
                        await service.process(ticket)
                        metrics.jobs.labels(kind, "processed").inc()
                        return
                    except Exception:
                        metrics.jobs.labels(kind, "retry").inc()
                        if attempt == 2:
                            raise
                        await asyncio.sleep(.2 * 2**attempt)
            except Exception as exc:
                log.exception("Job retained for recovery")
                metrics.jobs.labels(kind, "deferred").inc()
                await service.queue.publish("registration_dlq", {
                    "body":message.body.decode(), "error_type":type(exc).__name__})
            finally:
                metrics.job_duration.labels(kind).observe(time.perf_counter()-started)
    for name in ("registration_queue", "drop_queue"):
        queue = await channel.get_queue(name)
        await queue.consume(consume)
    try:
        await asyncio.Future()
    finally:
        await service.queue.close()
        await service.store.redis.aclose(close_connection_pool=True)
        server.shutdown()
