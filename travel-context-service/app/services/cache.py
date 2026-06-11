from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TtlCache(Generic[T]):
    """Small in-memory TTL cache for external API responses."""

    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> Optional[T]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = CacheEntry(
            value=value,
            expires_at=time.time() + self.ttl_seconds,
        )
