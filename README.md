# Freeband MusicBrainz add-on

A metadata add-on for [Freeband](https://github.com/freeband-music/web),
an open-source music client, backed by the
[MusicBrainz](https://musicbrainz.org) API. It implements the
[Freeband add-on protocol](https://github.com/freeband-music/protocol)
(0.2.0).

It provides:

- search for tracks, albums and artists;
- artist, album and track metadata;
- cover art URLs pointing at the [Cover Art Archive](https://coverartarchive.org).

It supplies metadata only, no audio. It needs no configuration and no keys.

## Run

```
nix develop
just run          # http://localhost:7001
just test         # offline tests
```

Without Nix you need Python 3.12 and [uv](https://docs.astral.sh/uv/); the
commands in the `justfile` are plain `uv run` invocations.

Other commands, both of which need a checkout of the protocol repository at
`../protocol` (or at the path in `FREEBAND_PROTOCOL`):

```
just conformance  # check the running add-on against the protocol
just gen          # regenerate freeband_protocol/models.py
```

Optional environment variable (a `.env` file is loaded):

- `FREEBAND_CACHE_DIR`: where responses are cached (default `.dev/cache`).

## Install in the client

Start the add-on, then add the URL `http://localhost:7001` on the client's
Add-ons screen (the client fetches `/manifest.json` from it). For other
devices use the machine's LAN address instead of `localhost`.

## Known limitation

Searching for a track by title alone is unreliable: MusicBrainz has no
popularity ranking, so covers and live takes can come before the well-known
recording. Including the artist in the query works.

## API etiquette

The add-on follows the
[MusicBrainz API rate limiting rules](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting):

- every request carries an identifying `User-Agent`;
- requests are limited to one per second on average;
- responses are cached on disk, so repeated lookups do not reach MusicBrainz.

If you host this add-on, set your own application name and contact in
`USER_AGENT` in `freeband_common/musicbrainz.py`, so that MusicBrainz can
reach you rather than this project. Because of the rate limit, one instance
serving many users will be slow.

## Data and attribution

- Metadata comes from MusicBrainz. Its core data is released under CC0; some
  supplementary data is under CC BY-NC-SA. See
  <https://musicbrainz.org/doc/About/Data_License>.
- Cover images are served by the Cover Art Archive and belong to their
  respective rights holders. This add-on returns their URLs and does not
  copy or host them.
- This project is not affiliated with or endorsed by the MetaBrainz
  Foundation. "MusicBrainz" is a trademark of the MetaBrainz Foundation.

## Licence

GNU General Public License v3.0 or later (GPL-3.0-or-later). See `LICENSE`.
