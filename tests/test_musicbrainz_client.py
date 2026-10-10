import asyncio

import httpx

from freeband_common.cache import Cache
from freeband_common.musicbrainz import USER_AGENT, MusicBrainz


def test_second_identical_call_is_served_from_cache(tmp_path):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "x"})

    async def no_sleep(seconds):
        raise AssertionError("should not sleep")

    async def run():
        client = MusicBrainz(
            transport=httpx.MockTransport(handler),
            cache=Cache(tmp_path),
            clock=lambda: 0.0,
            sleep=no_sleep,
        )
        first = await client.get("artist/x", {"inc": "aliases"})
        second = await client.get("artist/x", {"inc": "aliases"})
        return first, second

    first, second = asyncio.run(run())
    assert first == second == {"id": "x"}
    assert len(requests) == 1
    assert requests[0].headers["user-agent"] == USER_AGENT
    assert requests[0].url.params["fmt"] == "json"
