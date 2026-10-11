import os
import json
from typing import Optional, Dict, Any
import aio_pika

class RabbitMQManager:
    _instance: Optional["RabbitMQManager"] = None
    _connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
    _channel: Optional[aio_pika.abc.AbstractRobustChannel] = None

    def __init__(self, amqp_url: Optional[str] = None):
        self.amqp_url = amqp_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    @classmethod
    def get_instance(cls, amqp_url: Optional[str] = None) -> "RabbitMQManager":
        if cls._instance is None:
            cls._instance = cls(amqp_url)
        return cls._instance

    async def get_channel(self) -> aio_pika.abc.AbstractRobustChannel:
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self.amqp_url)
            self._channel = await self._connection.channel()
            # Khởi tạo các hàng đợi cơ sở
            await self._channel.declare_queue("registration_queue", durable=True)
            await self._channel.declare_queue("drop_queue", durable=True)
            await self._channel.declare_queue("registration_dlq", durable=True)
        return self._channel

    async def publish(self, queue_name: str, payload: Dict[str, Any]) -> None:
        channel = await self.get_channel()
        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json"
        )
        await channel.default_exchange.publish(message, routing_key=queue_name)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            self._channel = None
