"""Shared MusicBrainz client: identifying User-Agent, throttle, 503 retry, cache."""

import asyncio
import json
import time

import httpx

from .cache import Cache

BASE_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "Freeband/0.1 ( https://github.com/freeband-music/addon-musicbrainz )"
CACHE_TTL = 7 * 24 * 3600
RATE = 1.0  # requests per second
BURST = 3
RETRIES = 3
RETRY_WAIT = 2.0


class MusicBrainzError(Exception):
    """MusicBrainz could not be reached or answered with an error."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class NotFound(MusicBrainzError):
    """MusicBrainz does not know the entity (HTTP 400 or 404)."""


class TokenBucket:
    def __init__(self, rate: float, burst: int, clock, sleep) -> None:
        self._rate = rate
        self._burst = burst
        self._clock = clock
        self._sleep = sleep
        self._tokens = float(burst)
        self._last = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self._burst, self._tokens + (now - self._last) * self._rate)
        self._last = now

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1:
                await self._sleep((1 - self._tokens) / self._rate)
                self._tokens = 1.0
                self._last = self._clock()
            self._tokens -= 1


class MusicBrainz:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        cache: Cache | None = None,
        clock=time.monotonic,
        sleep=asyncio.sleep,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            transport=transport,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        self._cache = cache if cache is not None else Cache()
        self._sleep = sleep
        self._bucket = TokenBucket(RATE, BURST, clock, sleep)

    async def get(self, path: str, params: dict | None = None) -> dict:
        params = {k: str(v) for k, v in (params or {}).items()}
        key = "mb:" + path + "?" + json.dumps(sorted(params.items()))
        cached = self._cache.get(key)
        if cached is not None:
            return json.loads(cached)
        for attempt in range(RETRIES + 1):
            await self._bucket.acquire()
            try:
                response = await self._http.get(
                    "/" + path.lstrip("/"), params={**params, "fmt": "json"}
                )
            except httpx.HTTPError as exc:
                raise MusicBrainzError(f"{type(exc).__name__}: {exc}") from exc
            if response.status_code == 503 and attempt < RETRIES:
                await self._sleep(RETRY_WAIT)
                continue
            if response.status_code in (400, 404):
                raise NotFound(f"MusicBrainz HTTP {response.status_code}", response.status_code)
            if response.status_code != 200:
                raise MusicBrainzError(
                    f"MusicBrainz HTTP {response.status_code}", response.status_code
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise MusicBrainzError("MusicBrainz returned invalid JSON") from exc
            self._cache.set(key, json.dumps(data), CACHE_TTL)
            return data
        raise AssertionError("unreachable")


_shared: MusicBrainz | None = None


def shared() -> MusicBrainz:
    """The process-wide client, so every caller shares one throttle."""
    global _shared
    if _shared is None:
        _shared = MusicBrainz()
    return _shared
