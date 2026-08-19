---
name: still-tok
description: Make a short vertical video out of generated stills instead of generated video - a Ken Burns slideshow. One painted still per fact, each held a few seconds with a slow pan or zoom, and the fact itself physically built into the scene as carved, embossed, traced or worn text rather than composited on top. Use when the user wants a fact video, an emotional explainer, a slideshow video, a carousel, or says "still video", "picture video", "ken burns", "one fact per picture", or wants a video without paying for video generation.
---

# still-tok

A video made of stills. One picture per fact, each held three or four seconds with a slow move
on it, cut together with ffmpeg. No video model anywhere in the pipeline.

Why it beats generated video for this job:

- A still costs cents. Nine seconds of generated video costs dollars. You can afford to reject
  a bad frame.
- A still holds a style exactly. Video models drift, warp geometry, and lose the palette.
- The text can live inside the picture, which is the whole point of the format.

## The one rule

**The words are part of the world, not on top of it.**

Never composite a caption. Ask the image model to build the sentence into the physical scene, so
it reads as something that was there when the shutter opened. This is the entire creative
difference between this format and every other fact video.

Good materials, one per still, never repeated inside a video:

- traced by a fingertip in the condensation on a cold window, drips running from the strokes
- pressed blind into thick paper, no ink, caught by raking light
- carved into a wooden bench slat, worn smooth at the edges
- brushed into the pile of a carpet, the way a vacuum leaves stripes, readable only by nap direction
- written in the dust on a car panel or a shelf
- formed by the gap between roof tiles, floorboards, or bricks with the mortar missing
- pressed into wet sand, cement, or snow
- the shadow of something else falling into the shape of the words
- steam cleared from a bathroom mirror
- the wear pattern worn into a painted step by thousands of feet
- rust bleeding through paint in the shape of the letters
- frost on the inside of a pane

Rules for the text:

- One sentence per still. Six to ten words. It has to be readable at arm's length on a phone.
- Lowercase reads softer and more human. Uppercase reads like a warning.
- Put it where the eye already goes. It should be found, not announced.
- Say the material and the light in the prompt. "carved" alone gives you a sign. "carved into the
  worn wooden armrest of an airport bench, raking evening light in the grooves" gives you a scene.
- Do not say "readable" or "legible" in the prompt. Say what the light is doing instead.

## Length and count

**Four facts is the number.** Three feels thin, five overstays. At three and a half seconds a
still, four facts plus a two second end card is about sixteen seconds.

That is longer than a nine second loop and it is the right trade here, because a person has to
*read*. Under three seconds a card cannot be read and the video fails silently. Over four and a
half and the viewer is waiting.

| Beat | Time | Job |
| --- | --- | --- |
| 1 | 0.0 - 3.5s | the fear, named. the thing they already feel |
| 2 | 3.5 - 7.0s | the second fact, turning the screw |
| 3 | 7.0 - 10.5s | the fact that costs the most to not know |
| 4 | 10.5 - 14.0s | the turn. what this all means about them |
| card | 14.0 - 16.0s | who you are. only if it earns its place |

## Emotion beats humour here

Humour needs timing the format does not have. A still held for three seconds cannot land a
punchline, because the surprise and the safety cannot arrive together on a held frame.

What the format is good at is weight. A quiet picture and a hard sentence, held long enough to
sink. Build the four beats as one emotional argument, not four unrelated facts. The last card
should say something about the viewer, not about the subject.

## Motion

Every still moves. A static still reads as a broken video and gets scrolled.

- Slow push in, or slow pull out. About 6% travel over the hold. More than that reads as a zoom.
- Or a slow drift, right to left, about 4% of the frame width.
- Alternate direction between cards so the video breathes instead of marching.
- Never move on the same axis three times in a row.
- Crossfade about 0.35s, centred on the cut so the change lands on the strike. A hard cut is too
  abrupt for an emotional piece; anything longer than half a second reads as a slideshow dissolve.
- The picture always fills the frame. Generate at 9:16 and never letterbox.

## Music, and cutting to it

Use a trending sound, added **in the TikTok app at upload**, not muxed into the file.

The reason is not the music. It is that TikTok links a video to the sound's page, and that page
is a discovery surface. Burn the audio into the mp4 and you get the song without the link, which
is the half that does nothing. A generated track is worse still, because nobody is searching for
it.

So: build the file with a quiet ambient bed or no audio, and hand the user an upload instruction.
Generate music only when the video has to work as a standalone file somewhere that is not TikTok.

**Cut on instrument hits, not on a timer.** A fixed hold reads as a slideshow. A cut that lands on
a piano strike reads as authored. Get the audio, transcribe it, and snap each cut to the nearest
strong onset.

```bash
~/.local/bin/yt-dlp -x --audio-format wav \
  --extractor-args "youtube:player_client=android,web_safari" -o "snd.%(ext)s" <url>
~/.venvs/beat/bin/python trans.py snd.wav      # muscriptor, per instrument note starts
```

MuScriptor lives at `~/i/muscriptor`. Despite the README, **it needs no `HF_TOKEN`** — the weights
download anonymously. Install it into a venv that already has torch, add `soundfile` or its audio
loader fails with a bare "Could not load audio". The API is `TranscriptionModel.load_model(device=
"cpu")`, then `.transcribe(path)` yields `NoteStartEvent` objects carrying `start_time`, `pitch`,
and `instrument`.

**A hit is a chord, not a note.** Group note starts by timestamp. Where four or more pitches start
together, that is a strike you can hear. Two notes is not. Cut on the four-plus ones.

`beat-this` gives the tempo grid and is worth running as a cross-check — the strong strikes should
land on downbeats. It is the grid, though, not the hits. Do not cut on it alone.

**Hold the reading floor.** Snap each cut to the nearest strike within about half a second of the
ideal time, and never let a hold fall below three seconds, or the card cannot be read. If the
nearest strike would break that, take the next one.

**Tell the user where to start the sound.** The sync only holds if they trim the sound to the strike
you measured from. Put that timestamp in the handover.

## Facts

Every fact must be real and checkable. Pull from the client's own published pages first, so the
video and the site agree, and the video is a reason to visit the site.

Never invent a fact, a number, a deadline, or a legal claim. If a fact cannot be sourced, cut it
and use three.

## Pipeline

```bash
node still.mjs pic  <spec.json> 0      # one still, review it, then do the rest
node still.mjs pic  <spec.json> all    # the remaining stills
node still.mjs cut  <spec.json>        # ken burns, cuts, assembly, ffmpeg only, free
```

Generate **one still first and look at it**. Text inside a scene is the part that fails, and it
fails the same way on every card in a batch. One rejected batch costs more than one test.

## Found in practice

Notes from building the first one. Update this section every time you build another.

**Two models, two passes.** The style and the spelling do not come from one model. A cheap painterly
model gets the house look but garbles words. A strong model spells correctly but drifts photoreal.
So: pass one, the cheap model paints the whole scene *including the sentence*, badly spelled. Pass
two, hand that painting to the strong model as an image reference and have it redraw only the
lettering.

**Do not give the strong model a blank surface.** It sounds right and it is wrong. Asked to *add*
words to a clean painting, it lays down flat typographic captions sitting on top of the scene,
which is the exact thing the format exists to avoid. Asked to *fix* words already painted into a
material, it keeps the material. The garbled first pass is doing real work: it establishes that
the letters are worn, embossed, or traced, and where.

**Pass two has to defend the style as well as fix the words.** The strong model repaints while it
letters, and it repaints towards photoreal — realistic concrete, fabric weave, depth of field. The
pass two prompt has to carry its own style defence: keep it a flat painted animation frame, do not
repaint any surface realistically, do not add photographic texture or render sheen, the only thing
you change is the lettering. Without that line one card in three comes back as a 3D render.

**Pass two has to be given permission to destroy.** "Correct the lettering" leaves the garble
untouched. What works is telling it the writing is misspelled nonsense, and to erase it completely
and redraw it from scratch.

**The style lock decides everything, and its wording is fussy.** Calling it "a painting, not a
photograph, an oil illustration on canvas" produces thick van Gogh impasto, which is a different
look. What produces flat painted planes is naming what it actually is:

> THIS IS A SINGLE FRAME FROM A PAINTED 3D ANIMATED FEATURE FILM. it is not a photograph, not live
> action, and not an oil painting on canvas. it is animation. every surface is built from flat
> simplified planes of painted colour with soft painted edges, the way a background painter blocks
> in a shape. there is no photographic surface texture, no visible fabric weave or carpet fibre, no
> volumetric light shafts or god rays, no realistic depth of field, no render sheen and no specular
> highlights. light falls as broad flat painted shapes, not as simulated beams.

**Carve it, do not mark it.** Words that sit on a surface read as a caption no matter how you dress
them. Words cut *into* a surface read as part of the world. Three things make the difference, and
all three have to be in the prompt:

1. **Shadow inside the groove, and a lit edge along one side of every stroke.** This is what the eye
   reads as depth. Name which direction the light comes from.
2. **Cut through a layer.** Not "carved into the door" but gouged through the paint into the bare
   wood beneath, through the varnish into raw pale wood, through the surface of the slab.
3. **Imperfection.** Wandering depth, crooked strokes, doubled cuts where the blade slipped, chipped
   edges, torn grain, splinters standing up, grime settled in the bottoms. A clean even engraving
   still reads as machine-made type.

Embossing works the same way and is the gentlest version of it: raised and sunken shapes catching a
low raking light, no ink at all. That one holds up best on paper.

**Name the material and name the light.** The material alone gives you a sign hanging in the scene.
"worn into the painted concrete floor, the paint rubbed away by thousands of feet walking the same
line to the gate, catching the low dawn light" gave back lettering lying in correct floor
perspective. That perspective is what sells it.

**Put a person in it.** An object alone does not carry a sentence. An empty armchair meant nothing;
the same line over a woman sat on the floor among opened letters means everything. The style holds
up well with faces, and a face gives the key light something to do.

**Keep the sentence away from the frame edge.** The Ken Burns move crops about 6%, so text that
reaches the edge gets clipped mid-word once it is moving. Either pull it inboard in the prompt, or
give that card a push *in*, which starts at zoom 1.0 and is uncropped at the moment people read it.

**Cost, measured.** The painting pass runs about 1.5 cents and the lettering pass about 4, so a
card is roughly 5.5 cents and a clean four card video is **about 22 cents**. Everything after the
stills is free: the audio download, the transcription, the Ken Burns moves, and the assembly all
run locally.

Building the format the first time cost **92 cents**, four times a clean run, and all of the
difference went on abandoned directions: a wrong style lock that produced impasto, a text-free
experiment that produced flat captions, and two cards that needed replacing on concept. Budget for
that on a new look. Once the spec is settled, a new episode is 22 cents.

Watch the reading, not the price. At these numbers rejecting a still costs less than shipping a bad
one, so reject freely.

**Check the end card for wrapping.** A brand name that fits on the design comp will orphan its
last word at video width. Render it and look.

## What kills these

- Composited captions. The format is gone the moment text sits on top.
- Text the model garbles. Look at every still. Half-formed letters read as AI instantly.
- A still that does not move.
- Five or more facts.
- A hold under three seconds. Nobody could read it.
- An end card that is longer than the fact it follows.
