from freeband_common.albums import rank_release_groups

ARTIST = {"artist-credit": [{"artist": {"id": "a1", "name": "Joy Division"}}]}
VARIOUS = {"artist-credit": [{"artist": {"id": "va", "name": "Various Artists"}}]}


def release(group_id, primary, date, credit, secondary=(), status="Official"):
    return {
        "status": status,
        "date": date,
        **credit,
        "release-group": {
            "id": group_id,
            "primary-type": primary,
            "secondary-types": list(secondary),
        },
    }


def test_own_studio_album_beats_earlier_compilation():
    releases = [
        release("comp", "Album", "1979", VARIOUS, ["Compilation"]),
        release("studio", "Album", "1988-06", ARTIST),
        release("studio", "Album", "1980-07-18", ARTIST),
    ]
    assert [g["id"] for g in rank_release_groups(releases, {"a1"})] == ["studio", "comp"]


def test_single_only_track_falls_back_to_artists_single():
    releases = [
        release("comp", "Album", "1985", VARIOUS, ["Compilation"]),
        release("single", "Single", "1995", ARTIST),
    ]
    ranked = rank_release_groups(releases, {"a1"})
    assert [g["id"] for g in ranked] == ["single", "comp"]
    assert ranked[0]["artist-credit"] == ARTIST["artist-credit"]
