# Source directory for artist style research

Ordered by evidence quality. Tiers 1–2 document mechanisms; everything below describes results.

## Tier 1 — production mechanism

Where engineers explain what they actually did. The highest-value tier by a wide margin.

| Source | Holds | How to search |
|---|---|---|
| **Sound on Sound** — *Classic Tracks*, *Inside Track* | Track-by-track breakdowns: mics, preamps, compressors, room, take counts, mix moves | `"<artist>" "sound on sound" classic tracks` / `soundonsound.com "<album>"` |
| **Tape Op** | Long-form engineer and producer interviews, indie and analogue-leaning | `tapeop "<producer>"` |
| **Mix**, **Recording Magazine** | Studio reports, gear chains | `"<album>" mix magazine recording` |
| **Producer interviews generally** | The mechanism behind a signature | `"<producer>" interview recording "<album>"` |

## Tier 2 — credits and facts

Who was in the room. The same engineer across a discography usually *is* the sound.

| Source | Holds |
|---|---|
| **Discogs** | Full personnel per release, pressing detail, studio |
| **MusicBrainz** | Structured relationship data — performer, engineer, producer, studio |
| **AllMusic** | Credits plus a style/mood taxonomy |
| **Genius** | Credits, sample identification, producer annotations |
| **WhoSampled** | Sample sources and who sampled them back — traces lineage in both directions |

## Tier 3 — music theory

| Source | Holds |
|---|---|
| **Hooktheory TheoryTab** | Crowd-transcribed chord progressions and keys, searchable by artist. The fastest route to harmonic habits |
| **Academic musicology** | Google Scholar for canonical or heavily studied artists |
| **Transcription YouTube** | Channels that transcribe before analysing. Discount anything that analyses by vibe |

## Tier 4 — artist on process

Podcasts where artists narrate their own decisions. Rich, but self-report — the artist's story about a choice and the engineer's account of it often differ.

**Song Exploder** · **Tape Notes** · **Broken Record** · **Rick Beato** · label mini-docs and album commentaries

## Tier 5 — genre placement

| Source | Holds | Caveat |
|---|---|---|
| **Every Noise at Once** (everynoise.com) | ~6,000 micro-genre names with the artists clustering in each. Unmatched for naming a scene precisely | Frozen since December 2023 — no artists or genres added after that. The taxonomy itself is still the best available |
| **RateYourMusic** | User genre tags, descriptor tags, influence graphs | Crowd opinion |

Micro-genre names are the highest-leverage output of this tier. A named scene carries production convention, instrumentation, and era in one or two words.

## Tier 6 — critical vocabulary

AllMusic style/mood tags, Pitchfork, The Quietus, Stereogum, Resident Advisor. Use for `[C]` claims and for borrowing precise descriptive language. Never for mechanism.

## Measured data

| Want | Use |
|---|---|
| BPM and key per track | **TuneBat**, **SongBPM** |
| Tempo, key, time signature via API | **Apple Music API** (needs a paid developer account) |
| Full acoustic analysis from audio you hold | **Essentia** — open-source MIR toolkit, the one Spotify built its own features on. Returns BPM, key, danceability, loudness, dynamic complexity, onset rate |
| Bulk historical analysis | **AcousticBrainz** public dump, ~7.5M tracks, one-time release July 2022 |

**Spotify's `audio-features` endpoint is deprecated** — restricted to apps created before November 2024, no official replacement. Don't build on it.

## Search patterns that work

```
"<artist>" "sound on sound"
"<album>" recording engineer interview
"<producer>" gear chain "<artist>"
site:discogs.com "<album>" credits
"<artist>" hooktheory chord progression
"<artist>" site:everynoise.com
"<artist>" analysis transcription
```

## Where research usually goes wrong

- **Averaging across eras.** Segment first, always.
- **Trusting the artist's own account of the mechanism.** They remember intent; the engineer remembers signal path.
- **Collecting adjectives.** If a paragraph could describe fifty artists, it has no content.
- **Skipping negative space.** What an artist never does is often the sharpest identifier available, and almost nobody writes it down.
- **Stopping at the famous album.** The signature is what recurs across the catalogue, not what happened once.
