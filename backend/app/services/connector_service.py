"""Provider-neutral read interface and opt-in tenant-bound Slack sandbox adapter."""
from dataclasses import dataclass
import json
import math
import re
import threading
import time
from typing import Protocol

import httpx

from app.db.database import get_settings
from app.monitoring.tracing import span


class ConnectorUnavailable(RuntimeError):
    pass


class ConnectorRateLimited(RuntimeError):
    def __init__(self, retry_after=1):
        self.retry_after = max(1, min(int(retry_after), 3600))
        super().__init__("Connector rate limited")


class ReadConnector(Protocol):
    def read_page(self, resource_id: str, limit: int = 15, cursor: str = "") -> dict: ...


@dataclass(frozen=True, repr=False)
class SlackCredentials:
    token: str
    channels: frozenset[str]


def credentials(customer_id):
    try:
        raw = get_settings().slack_tenant_credentials.get_secret_value()
        if len(raw) > 64000:
            raise ValueError()
        mapping = json.loads(raw)
        if not isinstance(mapping, dict) or len(mapping) > 100:
            raise ValueError()
        value = mapping.get(str(customer_id))
        if not isinstance(value, dict):
            raise ValueError()
        token, channels = value.get("bot_token"), value.get("channel_ids")
        if not isinstance(token, str) or not token.startswith("xoxb-") or not 10 <= len(token) <= 512:
            raise ValueError()
        if not isinstance(channels, list) or not 1 <= len(channels) <= 50 or any(
            not isinstance(channel, str) or not re.fullmatch(r"[CG][A-Z0-9]{8,31}", channel) for channel in channels):
            raise ValueError()
        return SlackCredentials(token, frozenset(channels))
    except (ValueError, TypeError, AttributeError):
        raise ConnectorUnavailable("Tenant Slack connector is not configured") from None


class ReadRateLimiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.next_at = {}

    def take(self, customer_id):
        now = time.monotonic()
        with self.lock:
            remaining = self.next_at.get(customer_id, 0) - now
            if remaining > 0:
                raise ConnectorRateLimited(math.ceil(remaining))
            if len(self.next_at) >= 1024:
                self.next_at.pop(next(iter(self.next_at)))
            self.next_at[customer_id] = now + 1


rate_limiter = ReadRateLimiter()


class SlackReadConnector:
    URL = "https://slack.com/api/conversations.history"

    def __init__(self, customer_id, *, transport=None, sleep=time.sleep, limiter=None):
        self.customer_id = customer_id
        self.credentials = credentials(customer_id)
        self.transport, self.sleep = transport, sleep
        self.limiter = limiter or rate_limiter

    def read_page(self, resource_id, limit=15, cursor=""):
        if resource_id not in self.credentials.channels:
            raise PermissionError("Slack channel is not authorized for this tenant")
        if type(limit) is not int or not 1 <= limit <= 15 or not isinstance(cursor, str) or len(cursor) > 512 or not re.fullmatch(r"[A-Za-z0-9+/=_-]*", cursor):
            raise ValueError("Invalid connector pagination")
        self.limiter.take(self.customer_id)
        with span("connector.slack.read"):
            try:
                with httpx.Client(transport=self.transport, trust_env=False, follow_redirects=False,
                                  timeout=10) as client:
                    for attempt in range(2):
                        with client.stream("GET", self.URL,
                            headers={"Authorization": "Bearer " + self.credentials.token},
                            params={"channel": resource_id, "limit": limit, "cursor": cursor}) as response:
                            if response.status_code == 429:
                                try:
                                    delay = max(1, int(response.headers.get("Retry-After", "1")))
                                except ValueError:
                                    delay = 60
                                if attempt == 0 and delay <= 2:
                                    self.sleep(delay)
                                    continue
                                raise ConnectorRateLimited(delay)
                            if 500 <= response.status_code < 600 and attempt == 0:
                                self.sleep(.2)
                                continue
                            if response.status_code != 200:
                                raise ConnectorUnavailable("Slack read failed")
                            body = bytearray()
                            for chunk in response.iter_bytes(32768):
                                body.extend(chunk)
                                if len(body) > 1024 * 1024:
                                    raise ConnectorUnavailable("Slack response exceeds limit")
                            payload = json.loads(body)
                            if not isinstance(payload, dict) or payload.get("ok") is not True:
                                raise ConnectorUnavailable("Slack read failed")
                            messages = payload.get("messages", [])
                            if not isinstance(messages, list) or len(messages) > limit:
                                raise ConnectorUnavailable("Invalid Slack response")
                            items = []
                            for message in messages:
                                if not isinstance(message, dict) or not isinstance(message.get("text"), str) or not isinstance(message.get("ts"), str):
                                    raise ConnectorUnavailable("Invalid Slack message")
                                items.append({"text": message["text"][:4000], "timestamp": message["ts"][:40],
                                              "truncated": len(message["text"]) > 4000})
                            metadata = payload.get("response_metadata", {})
                            next_cursor = metadata.get("next_cursor", "") if isinstance(metadata, dict) else ""
                            if not isinstance(next_cursor, str) or len(next_cursor) > 512 or not re.fullmatch(r"[A-Za-z0-9+/=_-]*", next_cursor):
                                raise ConnectorUnavailable("Invalid Slack pagination")
                            return {"provider": "slack", "items": items, "next_cursor": next_cursor}
            except (httpx.HTTPError, ValueError, TypeError):
                raise ConnectorUnavailable("Slack read unavailable") from None
        raise ConnectorUnavailable("Slack read unavailable")
