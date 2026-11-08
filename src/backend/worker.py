import asyncio
import logging
from src.backend.infrastructure.messaging.worker_runtime import run_worker

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
