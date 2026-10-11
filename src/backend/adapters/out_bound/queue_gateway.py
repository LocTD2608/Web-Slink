from abc import ABC, abstractmethod
from typing import Dict, Any

class IQueueGateway(ABC):
    """Cổng giao tiếp trừu tượng tới RabbitMQ Message Broker."""
    
    @abstractmethod
    async def publish_registration_job(self, payload: Dict[str, Any]) -> None:
        """Đẩy công việc ghi danh sinh viên vào registration_queue."""
        pass

    @abstractmethod
    async def publish_drop_job(self, payload: Dict[str, Any]) -> None:
        """Đẩy công việc hủy môn học vào drop_queue."""
        pass
