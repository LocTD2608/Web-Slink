import json
import logging
import asyncio
from typing import Dict, Any
import aio_pika

from src.backend.adapters.out_bound.cache_gateway import ICacheGateway
from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway
from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
from src.backend.core.domain.entities.registration import Registration

logger = logging.getLogger(__name__)

class RegistrationConsumer:
    def __init__(
        self,
        rabbitmq_manager: RabbitMQManager,
        cache_gateway: ICacheGateway,
        persistence_gateway: IPersistenceGateway
    ):
        self.rmq = rabbitmq_manager
        self.cache = cache_gateway
        self.persistence = persistence_gateway

    async def start_consuming(self) -> None:
        channel = await self.rmq.get_channel()
        await channel.set_qos(prefetch_count=20) # Giới hạn 20 message đồng thời để bảo vệ DB
        queue = await channel.get_queue("registration_queue")

        logger.info("RegistrationConsumer started. Waiting for messages...")
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(requeue=False):
                    await self._process_message(message)

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        try:
            payload: Dict[str, Any] = json.loads(message.body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to decode message: {e}")
            return

        ticket_id = payload.get("ticket_id")
        student_id = payload.get("student_id")
        section_id = payload.get("section_id")
        semester_id = payload.get("semester_id")
        credits = payload.get("credits", 3)
        section_time_mask = payload.get("section_time_mask", 0)

        # Retry với Exponential Backoff (3 lần)
        max_retries = 3
        persisted = False
        last_error = ""

        for attempt in range(1, max_retries + 1):
            try:
                registration = Registration(
                    id=str(ticket_id),
                    ticket_id=ticket_id,
                    student_id=student_id,
                    section_id=section_id,
                    semester_id=semester_id,
                    status="CONFIRMED"
                )
                await self.persistence.save_registration(registration)
                persisted = True
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"Attempt {attempt}/{max_retries} failed for ticket {ticket_id}: {last_error}")
                if attempt < max_retries:
                    await asyncio.sleep(0.2 * (2 ** attempt))

        if persisted:
            # Thành công: Cập nhật vé CONFIRMED trên Redis
            await self.cache.set_ticket_status(ticket_id=ticket_id, status="CONFIRMED")
            logger.info(f"Ticket {ticket_id} persisted successfully in PostgreSQL.")
        else:
            # Thất bại bất khả kháng: Kích hoạt GIAO DỊCH BỒI HOÀN (COMPENSATING ROLLBACK)
            logger.error(f"Permanent failure for ticket {ticket_id}. Triggering compensating rollback...")
            try:
                # 1. Hoàn trả slot và tín chỉ trên Redis
                await self.cache.atomic_release_slot(
                    student_id=student_id,
                    section_id=section_id,
                    credits=credits,
                    section_time_mask=section_time_mask
                )
                # 2. Cập nhật trạng thái vé là FAILED kèm lý do
                await self.cache.set_ticket_status(
                    ticket_id=ticket_id,
                    status="FAILED",
                    reason="Không thể lưu trữ vào CSDL sau 3 lần thử lại. Slot đã được hoàn trả."
                )
                # 3. Đẩy thông điệp vào Dead-Letter Queue (DLQ)
                payload["error_reason"] = last_error
                await self.rmq.publish("registration_dlq", payload)
            except Exception as rollback_err:
                logger.critical(f"Critical error during compensating rollback for ticket {ticket_id}: {rollback_err}")
