"""Pure mappings from MusicBrainz JSON to protocol models."""

import unicodedata

from freeband_common.albums import best_tier, rank_release_groups
from freeband_protocol.models import (
    Album,
    AlbumSummary,
    Artist,
    ArtistSummary,
    Track,
    TrackSummary,
)

COVER_URL = "https://coverartarchive.org/release-group/{}/front-250"


def dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def artist_summary(artist: dict) -> ArtistSummary:
    return ArtistSummary(id=f"mbid:artist:{artist['id']}", name=artist["name"])


def credit_artists(entity: dict) -> list[ArtistSummary]:
    return [
        artist_summary(credit["artist"])
        for credit in entity.get("artist-credit") or []
        if credit.get("artist")
    ]


def credit_ids(entity: dict) -> set[str]:
    return {c["artist"]["id"] for c in entity.get("artist-credit") or [] if c.get("artist")}


def _year(date: str | None) -> int | None:
    return int(date[:4]) if date and date[:4].isdigit() else None


def album_summary(group: dict) -> AlbumSummary:
    return AlbumSummary(
        id=f"mbid:release-group:{group['id']}",
        title=group["title"],
        artists=credit_artists(group),
        year=_year(group.get("first-release-date")),
        cover=COVER_URL.format(group["id"]),
    )


def _releases(recording: dict) -> list[dict]:
    # Search results leave a release's credit out when it equals the recording's.
    credit = recording.get("artist-credit") or []
    return [
        release if release.get("artist-credit") else {**release, "artist-credit": credit}
        for release in recording.get("releases") or []
    ]


def recording_album(recording: dict) -> AlbumSummary | None:
    """The best album for a recording, from its `releases`."""
    ranked = rank_release_groups(_releases(recording), credit_ids(recording))
    return album_summary(ranked[0]) if ranked else None


def recording_query(q: str) -> str:
    """Lucene query for free text mixing title and artist words in any order.

    Every word must be in the title or the artist name, so most covers drop
    out when the artist is named. The boosts are tuned against the live API:
    the artist boost lifts the named artist over acts whose titles repeat the
    words; the weak phrase clause keeps exact titles over acts named like one.
    """
    words = q.replace('"', " ").replace("\\", " ").split()
    if not words:
        return q
    each = " AND ".join(f'(recording:"{w}" OR artist:"{w}"^1.3)' for w in words)
    return f'({each}) OR (recording:"{" ".join(words)}")^0.3'


def _song_key(recording: dict) -> tuple[str, str]:
    title = unicodedata.normalize("NFKD", recording.get("title") or "").casefold()
    credits = [c["artist"] for c in recording.get("artist-credit") or [] if c.get("artist")]
    return "".join(ch for ch in title if ch.isalnum()), credits[0]["id"] if credits else ""


def collapse_recordings(recordings: list[dict], limit: int = 10) -> list[dict]:
    """One recording per song (same normalised title and primary artist).

    Keeps the recording on the best-tier album, the one on most releases on a
    tie. Songs are ordered by how many releases their recordings are on, most
    first (ties keep the input order); then, among one artist's songs, those
    on the artist's own official studio album come first.
    """
    best: dict[tuple[str, str], tuple[tuple[int, int], dict]] = {}
    count: dict[tuple[str, str], int] = {}
    for recording in recordings:
        releases = _releases(recording)
        rank = (best_tier(releases, credit_ids(recording)), -len(releases))
        key = _song_key(recording)
        count[key] = count.get(key, 0) + len(releases)
        if key not in best or rank < best[key][0]:
            best[key] = (rank, recording)
    keys = sorted(best, key=lambda key: -count[key])
    slots: dict[str, list[int]] = {}
    for index, (_, artist_id) in enumerate(keys):
        slots.setdefault(artist_id, []).append(index)
    ordered = list(keys)
    for indexes in slots.values():
        studio_first = sorted(indexes, key=lambda i: best[keys[i]][0][0] != 1)
        for index, source in zip(indexes, studio_first):
            ordered[index] = keys[source]
    return [best[key][1] for key in ordered[:limit]]


def track_summary(recording: dict) -> TrackSummary:
    return TrackSummary(
        id=f"mbid:recording:{recording['id']}",
        title=recording["title"],
        artists=credit_artists(recording),
        album=recording_album(recording),
        duration_ms=recording.get("length"),
    )


def track(recording: dict) -> Track:
    return Track(**track_summary(recording).model_dump())


def _newest_first(groups: list[dict]) -> list[dict]:
    return sorted(groups, key=lambda g: g.get("first-release-date") or "", reverse=True)


def artist(artist_json: dict, groups: list[dict]) -> Artist:
    """Albums, EPs and singles; plain studio albums first, each part newest first."""
    wanted = [g for g in groups if g.get("primary-type") in ("Album", "EP", "Single")]
    for group in wanted:
        group.setdefault("artist-credit", [{"artist": artist_json}])
    plain = [
        g for g in wanted if g["primary-type"] == "Album" and not g.get("secondary-types")
    ]
    others = [g for g in wanted if g not in plain]
    return Artist(
        **artist_summary(artist_json).model_dump(),
        albums=[album_summary(g) for g in _newest_first(plain) + _newest_first(others)],
    )


def pick_release(releases: list[dict]) -> dict | None:
    """Representative release: official preferred, then earliest date."""
    if not releases:
        return None
    return min(
        releases,
        key=lambda r: (r.get("status") != "Official", r.get("date") or "9999"),
    )


def album(group: dict, release: dict) -> Album:
    summary = album_summary(group)
    tracks = []
    for medium in release.get("media") or []:
        for item in medium.get("tracks") or []:
            recording = item.get("recording") or {}
            tracks.append(
                TrackSummary(
                    id=f"mbid:recording:{recording['id']}",
                    title=item.get("title") or recording["title"],
                    artists=credit_artists(item) or credit_artists(recording),
                    album=summary,
                    track_number=item.get("number"),
                    disc_number=medium.get("position"),
                    duration_ms=item.get("length") or recording.get("length"),
                )
            )
    return Album(**summary.model_dump(), tracks=tracks)
