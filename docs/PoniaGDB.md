# PoniaGDB (Ponia Game Database) - plan

Status: planned, not implemented. Decided 2026-11-25.

## What it is
A versioned, read-only SQLite data pack, published as a GitHub Release asset. PoniaMDM downloads it and
looks games up locally. No server, no user accounts, works offline.

## Scope (first release = A + B)
- **A. Identification** - file hash (CRC32 / MD5 / SHA1) -> game id. Built from hash lists
  (No-Intro, Redump, MAME/FBNeo romset lists, libretro-database which is MIT). Facts only.
- **B. Text data** - names (English + Chinese), release date, players, genre, developer, publisher,
  description. Sources must have clean licenses: Wikidata (CC0), our own and community-written text
  (CC BY-SA), facts curated by hand. Chinese names / descriptions are the gap nobody else fills
  (hacks, Chinese translations, bootlegs).
- **Not in scope: C. Media** (box art, logos, screenshots, video). Not hosted by us. The user may fetch media
  into their own library from a source under their own account.

## Rules
- Never ship data or media derived from ScreenScraper (CC BY-NC-SA, non-commercial) or other sources whose terms
  forbid redistribution. LaunchBox / MobyGames / IGDB data stay out until their terms are verified.
- A shared developer key must never be used as a relay for all users; per-user accounts only.
- Hashes only identify official dumps. Hacks and translations are matched by file name and by user corrections
  that are contributed back to the pack.
- Contributions via GitHub issues / pull requests; CI validates the format; contributors agree to the data license.

## Pack format (draft)
`ponia-gdb-<version>.sqlite` with tables `game`, `rom_hash`, `name` (per language), `description` (per language),
`meta` (license + source per row). A `manifest.json` carries version, schema version and sha256.

## Phases
1. PoniaMDM: optional "look up" step on scan results using the user's own ScreenScraper account (local cache only).
2. PoniaGDB pack builder + download + local lookup; seed data from Ponia.Roms and hand-written Chinese text.
3. Open contributions.

## Open questions
- Whether the pack ships with a commercial Ponia edition (decides which sources are allowed).
- ScreenScraper terms must be read directly (not verified from search); consider asking them about data sharing.
