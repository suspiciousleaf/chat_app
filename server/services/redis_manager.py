import json
from pathlib import Path
import asyncio
import redis

from dotenv import load_dotenv

env_path = Path("..") / ".env"
if env_path.exists():
    load_dotenv(env_path)

REDIS_URL = "redis://localhost:6379/0"
REDIS_QUEUE = "chat_queue"


class RedisManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    async def enqueue_message(self, message: dict):
        message_as_string = json.dumps(message)
        await asyncio.to_thread(self.redis.rpush, REDIS_QUEUE, message_as_string)
        # await self.redis.rpush(REDIS_QUEUE, message)

    async def dequeue_message(self) -> str:
        return await asyncio.to_thread(self.redis.blpop, REDIS_QUEUE, timeout=0)
        # return await self.redis.blpop(REDIS_QUEUE, message)

    async def get_len(self, queue: str) -> int:
        return await asyncio.to_thread(self.redis.llen, queue)

    async def verify_connection(self) -> dict:
        """Verify if the Redis connection is working."""
        try:
            ping_result = await asyncio.to_thread(self.redis.ping)
            if ping_result:
                return {"status": True, "details": None}
        except redis.RedisError:
            return {"status": False, "details": "redis connection failed"}
