---
name: suno-prompt
description: Write prompts for Suno AI music generation — Style field, Lyrics with structure tags, Exclude list, and slider settings, based on Suno's own documentation. Use whenever the user wants to make, generate, or improve a song, beat, jingle, theme, instrumental, or soundtrack with Suno; asks for a "suno prompt", "song prompt", "style prompt", "meta tags", "lyrics with tags"; says their Suno output is wrong (too generic, wrong genre, wrong vocals, ignored the structure, drifts mid-song); or asks how to prompt Suno at all. Also use for Suno's per-song tools — Personas, Cover, Extend, Replace Section, Add Vocals, Remaster, Upload Audio, Custom Models.
---

# Suno prompting

Suno takes three separate inputs. Most bad output is the right words in the wrong box.

| Box | Carries | Does not carry |
|---|---|---|
| **Style of Music** | the whole song's sound — genre, tempo, instruments, production, vocal type | section-by-section direction |
| **Lyrics** | the words, `[Section]` tags, and per-moment context | the genre |
| **Exclude** (Advanced Options) | plain terms to keep out | anything you want |

Sliders sit under Advanced Options and shape how literally Suno reads all three.

## Deliver this

Always hand back paste-ready blocks, labelled by box, nothing else between them:

```
STYLE
120 BPM melodic deep house, warm analog basslines, organic percussion,
hypnotic shakers, airy female vocal, wide reverb, gradual build

LYRICS
[Intro]
(soft ambient pads, no drums)

[Verse]
<lines>

[Chorus]
<lines>

EXCLUDE
brass, spoken word, male vocals

SLIDERS
Weirdness 35%  ·  Style Influence 75%
```

Then one line on what to change if the first generation misses. Nothing more.

If the request is thin ("make me a sad song"), pick a defensible direction and ship **three** variants that differ on one axis each — genre, tempo, or vocal — rather than interrogating. One round of questions only when the subject matter itself is unknown.

## Style field

Current models (v4.5 and later) read conversational prose, not just keyword soup. Suno's own before/after:

- Old: `deep house, emotional, melodic`
- Now: `Create a melodic, emotional deep house song with organic textures and hypnotic rhythms. Begin with soft ambient layers, natural sounds, and a deep, steady groove. Build gradually with flowing melodic synths, warm basslines, and intricate, subtle percussion.`

Cover these, roughly in this order — early words carry the most weight:

1. **Tempo** — a BPM number stabilises rhythm more than any adjective
2. **Genre** — lead with it; sub-genre beats genre (`memphis soul` over `soul`)
3. **Rhythm feel** — swung, four-on-the-floor, half-time, syncopated
4. **Instruments by name** — `Rhodes`, `808s`, `nylon-string guitar`, not "some keys"
5. **Vocals** — gender, register, delivery. Combinations work: `male lead with female backup singers`
6. **Mood + production** — reverb, saturation, tape hiss, lo-fi, wide stereo

Specificity is the whole game. `happy pop song` produces the average of all happy pop songs. Every concrete noun narrows the target.

**Describe the sound, never name an artist.** Suno moderates generations and artist names get rejected — and the description works better anyway, because "breathy close-mic vocal over brushed drums and upright bass" is information the model can act on.

**Creative Prompt Boosting**: typing a rough style and tapping the icon at the top-right of the Style field makes Suno expand it. Fine as a starting point, then edit it down.

## Lyrics field

Structure tags in square brackets mark sections:

`[Intro]` `[Verse]` `[Pre-Chorus]` `[Chorus]` `[Bridge]` `[Instrumental Break]` `[Guitar Solo]` `[Outro]` `[End]`

They are strong hints, not commands — Suno follows them most of the time and occasionally ignores one. When a tag gets ignored, simplify its wording and regenerate rather than stacking more tags on top.

Current models also read **context** in the Lyrics box, so per-moment direction belongs here while the genre stays in Style. A parenthetical under a tag steers that section:

```
[Bridge]
(drums drop out, single piano, half-time)
```

Writing tips that survive contact with the model: keep lines singable and roughly even in syllable count, repeat the chorus verbatim so it lands as a hook, and leave the strongest image for the last line of the chorus. Write original lyrics — the user owns lyrics they supply.

For an instrumental, leave Lyrics empty and toggle Instrumental on; putting `[Instrumental]` in the lyrics box is not the same thing.

## Exclude field

Advanced Options → Exclude. Plain terms — instruments, genres, vocal styles — you do not want. No syntax. Use it when a generation keeps importing something you never asked for; that is faster than rewriting the Style field to fight it.

## Sliders

| Slider | Range | Baseline | Move it when |
|---|---|---|---|
| **Weirdness** | Safe → Chaos | 50% = normal | Down for predictable, radio-shaped output. Up for unconventional rhythms, odd melodies, distinctive vocal processing |
| **Style Influence** | Loose → Strong | — | Up to hold your style prompt tightly. Down to let Suno treat it as inspiration |
| **Audio Influence** | — | appears only with an audio upload | Up when the uploaded melody, phrasing, or vocal identity must carry through |

A generic result usually means Style Influence is too low, not that the prompt was too short.

## Diagnosing a bad generation

| Symptom | Fix |
|---|---|
| Generic, could-be-anything | Add BPM and 2–3 named instruments; raise Style Influence |
| Wrong genre entirely | Move genre to the front of the Style field; drop competing genre words |
| Ignores section structure | Simplify tag wording to plain `[Chorus]`; regenerate — tags are probabilistic |
| Drifts by the second minute | Put per-section direction in the Lyrics box, not the Style field |
| Right sound, wrong voice | Specify gender + register in Style; put the unwanted type in Exclude |
| Unwanted instrument keeps appearing | Exclude field, not more Style words |
| Too safe / too samey across tries | Raise Weirdness above 50% |
| Vocals bury the track | Ask for the mix: `vocals forward, sparse arrangement` |

Iterate on one variable at a time and compare — Suno's own advice is to make several versions with small prompt variations rather than expecting one perfect take.

## References

- `references/glossary.md` — Suno's official music glossary: tempo, dynamics, structure, harmony, genres, texture, vocal technique, production, advanced terms. Pull precise vocabulary from here instead of inventing adjectives.
- `references/features.md` — Personas, Covers, Extend, Crop, Replace Section, Add Vocals, Remaster, ReMi, Upload Audio, stems, Custom Models, Voices, My Taste. Read when the request is about reusing a sound or reworking an existing track rather than writing a fresh prompt.

Sources: [suno.com/hub](https://suno.com/hub/how-to-make-a-song), [help.suno.com](https://help.suno.com/en/categories/550017).
