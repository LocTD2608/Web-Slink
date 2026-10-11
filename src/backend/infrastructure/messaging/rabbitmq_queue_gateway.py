from typing import Dict, Any
from src.backend.adapters.out_bound.queue_gateway import IQueueGateway
from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager

class RabbitMQQueueGateway(IQueueGateway):
    def __init__(self, rabbitmq_manager: RabbitMQManager):
        self.rmq = rabbitmq_manager

    async def publish_registration_job(self, payload: Dict[str, Any]) -> None:
        await self.rmq.publish("registration_queue", payload)

    async def publish_drop_job(self, payload: Dict[str, Any]) -> None:
        await self.rmq.publish("drop_queue", payload)
