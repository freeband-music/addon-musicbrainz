"""Choose the album a recording belongs on. Pure."""


def _credited(entity: dict, artist_ids: set[str]) -> bool:
    return any(
        (credit.get("artist") or {}).get("id") in artist_ids
        for credit in entity.get("artist-credit") or []
    )


def _tier(release: dict, group: dict, artist_ids: set[str]) -> int:
    if not (_credited(release, artist_ids) or _credited(group, artist_ids)):
        return 5
    primary = group.get("primary-type")
    if primary == "Album":
        plain = not group.get("secondary-types") and release.get("status") == "Official"
        return 1 if plain else 2
    if primary in ("Single", "EP"):
        return 3
    return 4


def rank_release_groups(releases: list[dict], artist_ids: set[str]) -> list[dict]:
    """De-duplicated release groups of a recording's releases, best first.

    Order: the artist's own official studio albums, the artist's other albums
    (live, compilation), the artist's singles and EPs, then everything else
    (various-artist compilations, soundtracks), the artist's own releases of
    other types ahead of releases credited to someone else. Ties: earliest
    release first.
    Each returned group carries an `artist-credit`, taken from its release
    when the group itself has none.
    """
    best: dict[str, tuple[tuple[int, str], dict]] = {}
    for release in releases:
        group = release.get("release-group")
        if not group or not group.get("id"):
            continue
        key = (_tier(release, group, artist_ids), release.get("date") or "9999")
        if group["id"] not in best or key < best[group["id"]][0]:
            if not group.get("artist-credit") and release.get("artist-credit"):
                group = {**group, "artist-credit": release["artist-credit"]}
            best[group["id"]] = (key, group)
    return [group for _, group in sorted(best.values(), key=lambda item: item[0])]


def best_tier(releases: list[dict], artist_ids: set[str]) -> int:
    """Tier of the group `rank_release_groups` puts first: 1 (best) to 5, 6 if none."""
    return min(
        (
            _tier(release, release["release-group"], artist_ids)
            for release in releases
            if (release.get("release-group") or {}).get("id")
        ),
        default=6,
    )
