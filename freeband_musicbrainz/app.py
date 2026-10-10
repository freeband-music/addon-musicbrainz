"""MusicBrainz metadata add-on."""

import asyncio
import re
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from freeband_common.musicbrainz import MusicBrainzError, NotFound, shared
from freeband_protocol.models import Manifest, SearchResponse

from . import mapping

CORS = {"Access-Control-Allow-Origin": "*"}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

MANIFEST = Manifest(
    id="org.freeband.musicbrainz",
    name="MusicBrainz",
    version="0.1.0",
    description="Search and metadata from MusicBrainz",
    protocol_version="0.2.0",
    resources=["search", "meta"],
    id_prefixes=["mbid:"],
    configurable=False,
)

app = FastAPI(title="Freeband MusicBrainz add-on", docs_url=None, redoc_url=None)


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status, headers=CORS
    )


@app.middleware("http")
async def cors(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(CORS)
    return response


@app.exception_handler(NotFound)
async def on_not_found(request, exc):
    return error(404, "not_found", "No such ID")


@app.exception_handler(MusicBrainzError)
async def on_upstream(request, exc):
    return error(502, "upstream_error", str(exc))


@app.exception_handler(HTTPException)
async def on_http(request, exc):
    return error(exc.status_code, "not_found" if exc.status_code == 404 else "error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def on_invalid(request, exc):
    return error(400, "bad_request", "Invalid or missing query parameter")


@app.exception_handler(Exception)
async def on_error(request, exc):
    return error(500, "internal_error", "Internal error")


def mbid(value: str, kind: str) -> str:
    prefix = f"mbid:{kind}:"
    if not value.startswith(prefix) or not UUID.fullmatch(value[len(prefix):]):
        raise NotFound(f"Not a {kind} ID: {value}")
    return value[len(prefix):]


@app.get("/manifest.json")
async def manifest():
    return mapping.dump(MANIFEST)


SEARCHES = {
    "track": ("recording", "recordings"),
    "album": ("release-group", "release-groups"),
    "artist": ("artist", "artists"),
}


@app.get("/search")
async def search(q: str, type: Literal["track", "album", "artist"] | None = None):
    kinds = [type] if type else list(SEARCHES)
    mb = shared()
    params = {
        kind: {"query": mapping.recording_query(q), "limit": 100}
        if kind == "track"
        else {"query": q, "limit": 10}
        for kind in kinds
    }
    pages = await asyncio.gather(*(mb.get(SEARCHES[kind][0], params[kind]) for kind in kinds))
    found = {kind: page.get(SEARCHES[kind][1]) or [] for kind, page in zip(kinds, pages)}
    return mapping.dump(
        SearchResponse(
            tracks=[
                mapping.track_summary(r)
                for r in mapping.collapse_recordings(found.get("track", []))
            ],
            albums=[mapping.album_summary(g) for g in found.get("album", [])],
            artists=[mapping.artist_summary(a) for a in found.get("artist", [])],
        )
    )


@app.get("/meta/artist/{id}")
async def get_artist(id: str):
    artist_id = mbid(id, "artist")
    mb = shared()
    artist, groups = await asyncio.gather(
        mb.get(f"artist/{artist_id}"),
        mb.get("release-group", {"artist": artist_id, "limit": 100}),
    )
    return mapping.dump(mapping.artist(artist, groups.get("release-groups") or []))


@app.get("/meta/album/{id}")
async def get_album(id: str):
    mb = shared()
    group = await mb.get(
        f"release-group/{mbid(id, 'release-group')}", {"inc": "releases+artist-credits"}
    )
    chosen = mapping.pick_release(group.get("releases") or [])
    release = (
        await mb.get(f"release/{chosen['id']}", {"inc": "recordings+artist-credits"})
        if chosen
        else {}
    )
    return mapping.dump(mapping.album(group, release))


@app.get("/meta/track/{id}")
async def get_track(id: str):
    recording = await shared().get(
        f"recording/{mbid(id, 'recording')}",
        {"inc": "artist-credits+releases+release-groups"},
    )
    return mapping.dump(mapping.track(recording))
