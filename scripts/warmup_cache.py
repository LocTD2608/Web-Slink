import asyncio
from scripts.cache_rebuild import warmup_cache

if __name__ == "__main__":
    asyncio.run(warmup_cache())
