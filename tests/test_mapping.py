from freeband_musicbrainz import mapping

CREDIT = [{"name": "Band", "artist": {"id": "a1", "name": "Band"}}]
GROUP = {"id": "g1", "title": "LP", "first-release-date": "1980-07-18", "artist-credit": CREDIT}
RELEASE = {
    "id": "r1",
    "media": [
        {"position": 1, "tracks": [
            {"number": "A1", "title": "One", "length": 181000,
             "recording": {"id": "rec1", "title": "One", "artist-credit": CREDIT}},
        ]},
        {"position": 2, "tracks": [
            {"number": "1", "title": "Two", "length": None, "artist-credit": CREDIT,
             "recording": {"id": "rec2", "title": "Two (take)", "length": 200000}},
        ]},
    ],
}


def test_release_maps_to_album():
    album = mapping.dump(mapping.album(GROUP, RELEASE))
    assert album["id"] == "mbid:release-group:g1"
    assert album["year"] == 1980
    assert album["cover"] == "https://coverartarchive.org/release-group/g1/front-250"
    first, second = album["tracks"]
    assert (first["id"], first["trackNumber"], first["discNumber"], first["durationMs"]) == (
        "mbid:recording:rec1", "A1", 1, 181000)
    assert (second["trackNumber"], second["discNumber"], second["durationMs"]) == ("1", 2, 200000)
    assert first["album"]["title"] == "LP" and first["artists"][0]["id"] == "mbid:artist:a1"
    assert "tracks" not in first["album"]


def _recording(id, title, artist, group_type, secondary=(), by=None, count=1):
    credit = [{"name": artist, "artist": {"id": artist, "name": artist}}]
    release = {
        "id": f"rel-{id}",
        "status": "Official",
        "release-group": {
            "id": f"g-{id}", "title": id, "primary-type": group_type,
            "secondary-types": list(secondary),
        },
    }
    if by:
        release["artist-credit"] = [{"name": by, "artist": {"id": by, "name": by}}]
    return {"id": id, "title": title, "artist-credit": credit, "releases": [release] * count}


def test_collapse_recordings_one_per_song_studio_first():
    recordings = [
        _recording("cover-comp", "Song", "Other", "Album", by="Various"),
        _recording("titled-live", "Song (live)", "Band", "Album", ["Live"], count=3),
        _recording("live", "Song", "Band", "Album", ["Live"]),
        _recording("studio", "SONG!", "Band", "Album"),
    ]
    kept = [r["id"] for r in mapping.collapse_recordings(recordings)]
    assert kept == ["studio", "titled-live", "cover-comp"]
    hit = _recording("hit", "Song", "Famous", "Single", count=9)
    assert mapping.collapse_recordings(recordings + [hit])[0]["id"] == "hit"
