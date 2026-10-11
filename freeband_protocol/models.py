# Generated from protocol/openapi.yaml by 'just gen'. Do not edit.

from __future__ import annotations

from enum import StrEnum

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, confloat


class Resource(StrEnum):
    search = 'search'
    meta = 'meta'
    stream = 'stream'


class Manifest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    name: str
    version: str
    description: str | None = None
    protocol_version: str = Field(
        ...,
        alias='protocolVersion',
        description='Semver of the protocol the add-on implements',
    )
    resources: list[Resource]
    id_prefixes: list[str] = Field(
        ...,
        alias='idPrefixes',
        description='ID prefixes this add-on answers for. An empty array means any ID, which is the norm for stream add-ons.',
    )
    configurable: bool | None = None
    configuration_required: bool | None = Field(None, alias='configurationRequired')


class ArtistSummary(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    name: str
    image: AnyUrl | None = None
    popularity: confloat(ge=0.0, le=100.0) | None = Field(
        None,
        description='Optional, 0 (unknown to listeners) to 100 (among the most played).',
    )


class AlbumSummary(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    title: str
    artists: list[ArtistSummary]
    year: int | None = None
    track_count: int | None = Field(
        None,
        alias='trackCount',
        description='Number of tracks on the album, when known.',
    )
    cover: AnyUrl | None = None
    popularity: confloat(ge=0.0, le=100.0) | None = Field(
        None,
        description='Optional, 0 (unknown to listeners) to 100 (among the most played).',
    )


class TrackSummary(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    title: str
    artists: list[ArtistSummary]
    album: AlbumSummary | None = None
    track_number: str | None = Field(
        None,
        alias='trackNumber',
        description='Position on the disc; may be non-numeric, for example "A2"',
    )
    disc_number: int | None = Field(None, alias='discNumber')
    duration_ms: int | None = Field(None, alias='durationMs')
    isrc: str | None = Field(
        None, description='International Standard Recording Code, when known.'
    )
    popularity: confloat(ge=0.0, le=100.0) | None = Field(
        None,
        description='Optional, 0 (unknown to listeners) to 100 (among the most played).',
    )


class Artist(ArtistSummary):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    albums: list[AlbumSummary]


class Album(AlbumSummary):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    tracks: list[TrackSummary] = Field(..., description='Ordered as on the album')


class Track(TrackSummary):
    model_config = ConfigDict(
        populate_by_name=True,
    )


class SearchResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    tracks: list[TrackSummary]
    albums: list[AlbumSummary]
    artists: list[ArtistSummary]


class Quality(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    codec: str
    bitrate_kbps: int | None = Field(None, alias='bitrateKbps')
    lossless: bool
    bit_depth: int | None = Field(
        None, alias='bitDepth', description='Bits per sample when known, e.g. 16 or 24.'
    )
    sample_rate_hz: int | None = Field(
        None,
        alias='sampleRateHz',
        description='Sample rate when known, e.g. 44100 or 96000.',
    )


class Kind(StrEnum):
    exact = 'exact'
    edition = 'edition'
    loose = 'loose'


class Match(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    confidence: confloat(ge=0.0, le=1.0)
    kind: Kind


class Stream(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    title: str
    size_bytes: int | None = Field(None, alias='sizeBytes')
    quality: Quality
    match: Match
    url: AnyUrl


class Status(StrEnum):
    ok = 'ok'
    queued = 'queued'
    not_found = 'not_found'


class StreamResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    status: Status = Field(
        ...,
        description='`ok`: at least one stream is ready to play. `queued`: nothing is playable yet, but the add-on has started preparing the track; ask again later (never sent when the request had `queue=false`). `not_found`: nothing playable for this request.',
    )
    message: str | None = None
    streams: list[Stream] = Field(..., description='Ordered best first')


class Error(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    error: Error
