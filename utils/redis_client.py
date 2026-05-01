import redis
import json
from typing import Optional, Any
from logger import get_logger
from config import Redisconfig

logger = get_logger()

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            try:
                cls._instance.client = redis.Redis(
                    host=Redisconfig.REDIS_HOST,
                    port=Redisconfig.REDIS_PORT,
                    db=Redisconfig.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # Test connection
                cls._instance.client.ping()
                logger.info("Successfully connected to Redis.")
            except redis.ConnectionError as e:
                logger.warning(f"Could not connect to Redis: {e}. Falling back to DB-only.")
                cls._instance.client = None
        return cls._instance

    def set_cache(self, key: str, value: Any, ttl: int = 3600):
        if not self.client:
            return
        try:
            serialized_value = json.dumps(value)
            self.client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def get_cache(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def delete_cache(self, key: str):
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

redis_client = RedisClient()
