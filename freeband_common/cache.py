"""Tiny SQLite key/value cache with per-entry TTL."""

import os
import sqlite3
import time
from pathlib import Path


class Cache:
    def __init__(self, directory: str | Path | None = None, clock=time.time) -> None:
        directory = Path(directory or os.environ.get("FREEBAND_CACHE_DIR", ".dev/cache"))
        directory.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._db = sqlite3.connect(directory / "cache.sqlite", isolation_level=None)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache"
            " (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)"
        )

    def get(self, key: str) -> str | None:
        row = self._db.execute(
            "SELECT value, expires FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None or row[1] <= self._clock():
            return None
        return row[0]

    def set(self, key: str, value: str, ttl_seconds: float) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
            (key, value, self._clock() + ttl_seconds),
        )
