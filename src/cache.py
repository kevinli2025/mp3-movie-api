import json
import logging

import fakeredis

logger = logging.getLogger(__name__)


class MovieCache:
    def __init__(self):
        self.client = fakeredis.FakeRedis(decode_responses=True)

    def make_key(self, limit):
        return f"movies:limit:{limit}"

    def get(self, limit):
        key = self.make_key(limit)
        cached_text = self.client.get(key)

        if cached_text is None:
            logger.debug(f"Cache MISS: {key}")
            return None

        logger.debug(f"Cache HIT: {key}")
        response = json.loads(cached_text)
        return response

    def set(self, limit, response):
        key = self.make_key(limit)
        response_text = json.dumps(response)
        self.client.set(key, response_text, ex=90)

    def invalidate(self):
        self.client.flushdb()
        logger.debug("Invalidated movie cache")
