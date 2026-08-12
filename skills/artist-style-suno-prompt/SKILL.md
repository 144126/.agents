---
name: artist-style-suno-prompt
description: Turn an artist's style into working Suno prompts — research the sound with artist-style, translate it into Suno's Style, Lyrics, Exclude and slider settings, and write original songs in that idiom. Use when the user wants a Suno song that sounds like a particular artist, band, producer, era or scene; says "make a song like X", "suno prompt in the style of X", "I want that X sound", "recreate this vibe in suno"; wants a Persona built around an artist's sonic character; or has a Suno track that fails to land a specific artist's feel. Bridges the artist-style and suno-prompt skills.
---

# Artist style → Suno prompt

Two halves: find out what actually makes the sound, then say it in the words Suno responds to.

Run **`artist-style`** to build the profile. Apply **`suno-prompt`** for the field mechanics. This skill is only the translation layer between them, plus the one rule that governs both.

## The rule: technique travels, identity doesn't

The artist's name never enters any Suno box. Three separate reasons, all pointing the same way:

1. **Suno moderates generations and rejects artist names.** A prompt built on a name simply fails.
2. **Descriptors outperform names even where names work.** "Close-mic'd breathy baritone, brushed drums, upright bass, tape saturation" is information a model can act on. A name is a lookup that may not resolve.
3. **It produces better music.** Chord vocabulary, groove feel, mic technique, arrangement habits — these are craft, shared and learned, and working in someone's idiom is how music has always moved. Their name, their voice, and their actual lyrics are theirs.

So: extract the mechanism, discard the identity, and the user ends up with their own song in a lineage rather than a knockoff nobody wants.

## Translation table

Every profile dimension has exactly one destination. Getting this mapping right is most of the job — the usual failure is dumping the whole profile into the Style field.

| Profile dimension | Destination | Becomes |
|---|---|---|
| Micro-genre + lineage | **Style**, first words | the scene name, most specific version available |
| Rhythm — BPM, feel, swing | **Style**, early | a number plus a feel word |
| Instrumentation palette | **Style** | named instruments, 3–5 of them, the signature one first |
| Production signature | **Style** | recording medium, room, compression, reverb character |
| Vocals — register, timbre, delivery | **Style** | gender, register, technique, mic distance |
| Harmony and melody habits | **Style**, briefly | modal or chord character in a few words |
| Song architecture | **Lyrics** | the `[Section]` tag sequence and its proportions |
| Arrangement dynamics | **Lyrics** | parentheticals under tags — what enters, what drops |
| Lyrical craft | shapes the **original lyrics you write** | themes, POV, imagery domain, rhyme density, line length |
| Negative space | **Exclude** | the list, verbatim |
| How idiosyncratic the artist is | **Weirdness** | conventional → below 50%, unconventional → above |
| How tightly to hold the reference | **Style Influence** | usually 70–85% for a specific target |

The negative-space row is the one people skip and the one that fixes the most generations. An artist who never uses cymbals, or never uses synths, or never sings above a certain register — put that in Exclude and half the wrongness disappears at once.

## Worked shape

How a profile line becomes prompt text:

| Profile said | Goes to | As |
|---|---|---|
| `[D] Tracked to 16-track tape, drums in a small dead room, no click` | Style | `tape-saturated, tight dry drums in a small room, loose human timing` |
| `[D] Tempo range 88–96 BPM, heavily swung` | Style | `92 BPM, deep swung groove` |
| `[C] Songs open cold on a solo instrument for roughly 8 bars` | Lyrics | `[Intro]`<br>`(solo electric piano, 8 bars, no drums)` |
| `[D] No synthesizers anywhere in the catalogue` | Exclude | `synthesizers, drum machine` |
| `[C] Lyrics: second person, domestic imagery, no chorus` | your lyrics | direct address, kitchen-and-weather nouns, verse-only form |

## Writing the lyrics

Write **new** lyrics in the idiom. The profile gives you themes, POV, imagery domain, rhyme scheme, line length, and form — that's a generative recipe, and it's enough. Never adapt or lightly reword existing lyrics; that isn't style transfer, it's copying with extra steps, and it reads worse.

If the user supplies their own lyrics, keep them and translate only the sound.

## Push one dial

Before delivering, move one element deliberately away from the source — a tempo, an instrument, a form choice, the lyrical POV. Two reasons: a prompt that hits the reference exactly still produces something derivative, and the one deviation is usually where the track becomes the user's own.

Name the dial you moved in your handoff so they can move it back.

## Persona: the answer to "a whole album of this"

A Persona saves a song's vocals and style for reuse. So the workflow for anything past a single track is:

1. Iterate on **one** song until it lands
2. Save it as a Persona
3. Generate the rest from that Persona with new lyrics each time

That gives consistency across a body of work that re-pasting a Style field never will, because the Persona carries the vocal identity of the generation you approved. Details in `suno-prompt`'s `references/features.md`.

## Deliver

`suno-prompt`'s output contract — labelled `STYLE` / `LYRICS` / `EXCLUDE` / `SLIDERS` blocks, paste-ready. Then three short lines:

- the two or three profile findings doing the most work in this prompt, so the user knows what to protect while editing
- the dial you pushed
- the first thing to change if generation one misses

If the research turned up thin — no production documentation, no credits, mostly `[I]` — say that in one line up front. A prompt built on inference is a reasonable starting point, and the user should know which one they're holding.
