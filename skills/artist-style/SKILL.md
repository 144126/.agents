---
name: artist-style
description: Deep, evidence-graded research into a musical artist's style — production signature, instrumentation, rhythm, harmony, vocal technique, song architecture, lyrical craft, and what they never do. Use when the user asks what makes an artist sound like themselves, how an artist's production or songwriting works, to analyse or break down a band/producer/rapper/singer's style, to compare two artists' techniques, to name the micro-genre an artist sits in, or to build a style profile before writing music in that idiom. Triggers on "what makes X sound like X", "analyse X's style", "how does X produce", "X's songwriting techniques", "artist style profile", "break down X's sound".
---

# Artist style research

Goal: a profile precise enough that a musician could work in the idiom without ever hearing the artist. Vague adjectives fail that test. "Warm and nostalgic" is worthless; "16-track tape, drums in a small dead room, no click, bass DI'd through a tube compressor" is usable.

## Two honesty rules

**You cannot listen.** Everything here is synthesised from documentation — credits, producer interviews, transcriptions, published analysis. Say so, and grade accordingly. If the user can describe what they hear, that is primary evidence; ask them.

**Describe lyrics, never reproduce them.** "Second-person address to an absent person, near-exclusively concrete nouns, internal rhyme landing off-beat, no chorus" tells a songwriter far more than a quoted verse would, and it is the analysis rather than the artefact. Same for melodies — describe contour and interval, don't transcribe a whole hook.

## Evidence grading

Tag every claim. This is what separates a profile from a Wikipedia paraphrase:

- **[D] Documented** — credits, gear lists, an interview with the artist/producer/engineer, published transcription or theory analysis, measured BPM/key
- **[C] Consensus** — several independent critics or listeners describe it the same way, but nobody documented the mechanism
- **[I] Inferred** — your read, extrapolated from [D] and [C]

A profile that is all [I] is a guess wearing a lab coat. If a dimension has no evidence, write "no evidence found" — that is a real finding, and it stops the next person re-searching.

## Segment by era first

Artists change, and a profile averaged across twenty years describes nobody. Before researching, split the catalogue into 2–4 periods by producer, label, lineup, or technology shift, then ask which one the user means. If they don't know, profile the period they're most likely thinking of and note where the others diverge.

## The thirteen dimensions

Work through these. Depth over completeness — three dimensions with documented mechanisms beat thirteen filled with adjectives.

1. **Identity** — one sentence naming the thing only this artist does
2. **Era map** — the periods, and what changed at each boundary
3. **Production signature** — recording medium, room, mic technique, compression, reverb character, stereo width, mix density, mastering loudness, deliberate flaws
4. **Instrumentation palette** — specific instruments and models, signature textures, the one unexpected element
5. **Rhythm** — tempo range in BPM, groove feel, swing, time signatures, syncopation habits, whether they play to a click
6. **Harmony** — chord vocabulary, modal tendencies, key preferences, progressions they return to, how they handle cadences
7. **Melody** — range, contour, interval habits, motif reuse, relationship to the chord tones
8. **Vocals** — register, timbre, delivery, technique (belt, falsetto, melisma, whisper, flow), phrasing against the beat, ad-lib habits, doubling and stacking, harmony intervals
9. **Song architecture** — typical form, intro length, where the hook lands, how long before the first chorus, outro behaviour
10. **Arrangement dynamics** — the density curve: what enters when, what drops out, how a build is engineered
11. **Lyrical craft** — themes, POV, imagery domains, diction level, rhyme scheme and density, narrative vs impressionistic, line length. Described, never reproduced
12. **Negative space** — what they conspicuously never do. Usually absent from every writeup and often more diagnostic than what they do
13. **Lineage** — influences, contemporaries, descendants, and the precise micro-genre name for the scene they sit in

## Research protocol

Search in this order — the ordering matters, because the first two tiers are where mechanisms live and everything below is people describing the results.

1. **Producer and engineer interviews** — the single richest source. Sound on Sound's *Classic Tracks* and *Inside Track* series, Tape Op, Mix. Search `"<artist>" <album> "sound on sound"` or `<producer name> interview <album> recording`
2. **Credits databases** — Discogs, MusicBrainz, AllMusic, Genius. Who engineered, who played, what studio. The same three names recurring across a discography usually *is* the sound
3. **Theory analysis** — Hooktheory's TheoryTab database for chord progressions and keys, academic musicology, transcription-based YouTube analysis
4. **Artist interviews on process** — Song Exploder, Tape Notes, Broken Record, Rick Beato
5. **Genre placement** — Every Noise at Once for the precise micro-genre name, RateYourMusic tags
6. **Critical vocabulary** — AllMusic style/mood tags, reviews. Weakest tier, useful only for [C] claims

Tempo and key: TuneBat or SongBPM. Spotify's audio-features endpoint has been dead for new apps since November 2024 — don't route anyone there.

Full source directory with URLs and search patterns: `references/sources.md`.

Stop when new sources stop changing the profile. Three interviews saying the same thing is enough; a fourth is procrastination.

## Output

A profile document, dimensions in the order above, every claim tagged [D]/[C]/[I], each dimension one tight paragraph or a short bullet list. Open with the one-sentence identity. Close with an evidence log: what you read, and what you looked for and could not find.

Where a dimension is genuinely thin, say so in one line and move on. Padding a weak section is how a research document becomes a horoscope.
