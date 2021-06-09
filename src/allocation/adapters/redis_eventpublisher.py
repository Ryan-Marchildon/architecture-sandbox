import json
from dataclasses import asdict
import redis

from src.allocation import config
from src.allocation.domain import events
from src.utils.logger import log


r = redis.Redis(**config.get_redis_host_and_port())


def publish(channel, event: events.Event):
    log.debug("publishing: channel=%s, event=%s", channel, event)
    r.publish(channel, json.dumps(asdict(event)))
