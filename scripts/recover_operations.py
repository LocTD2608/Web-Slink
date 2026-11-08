import asyncio, argparse
from src.backend.infrastructure.bootstrap import build_service

async def recover(age, limit):
    service, _ = build_service()
    try:
        print(await service.recover_pending(age, limit))
    finally:
        await service.queue.close()
        await service.store.redis.aclose(close_connection_pool=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--age", type=int, default=10)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(recover(args.age, args.limit))
