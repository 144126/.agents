---
name: memphis-tok
description: Make a short corporate-memphis style TikTok video built to go viral, with Seedance 2.0. Flat vector figures, brand colours only, 9 seconds by default, captions burned in with the real brand font. Use when the user wants a TikTok, Reel, or Short in flat illustration or corporate memphis style, wants an animated explainer for a brand, says "make a tiktok", "make a viral video", "corporate memphis video", "flat animation ad", or names a brand preset.
---

# memphis-tok

One video. Nine seconds. Flat vector. Brand colours only. Built to loop.

The video model draws the picture and nothing else. Every letter on screen is burned in
afterwards from the brand font, because video models garble text and garbled text kills a
brand video. Never ask the model for words.

## The nine seconds

Nine seconds is the default because completion rate decides reach. TikTok in 2026 wants
70%+ completion, up from 50% in 2024. Watch time and completion drive 40-50% of ranking,
and 63% of the best performing videos land the hook inside the first three seconds. A nine
second video that loops cleanly reads as over 100% completion. A thirty second video that
loses half the room reads as failure.

Three beats, hard cuts, no fade:

| Beat | Time | Job |
|---|---|---|
| hook | 0.0 - 1.2s | one line that costs the viewer something. a number, a loss, a wrong belief |
| turn | 1.2 - 6.0s | the single fact. one idea only. never two |
| sting | 6.0 - 9.0s | the consequence, then the loop line |

Rules that carry the beats:

- Motion starts on frame one. No logo intro, no black frame, no build.
- Around 24 spoken words fit in nine seconds. Write 20 and leave air.
- The last frame must match the first frame, so the loop is invisible.
- One idea. If the script needs "and", cut one half.
- The hook is a claim, never a greeting and never a topic label.

Override the length when the user asks: `--dur 12`. Allowed range is 5 to 20.

## The style lock

Corporate memphis is flat geometric illustration with tiny heads, long bendy limbs, no
faces, and non-human skin colour on flat solid backgrounds. Video models drift towards
photoreal 3D unless the prompt fights it in every clause. Paste this block into every
prompt, unchanged, and put the shot description after it.

```
flat vector motion graphic, corporate memphis illustration, strictly 2D.
figures: tiny heads, no facial features, long noodle limbs with rounded bends,
oversized hands, blocky torsos, skin filled with a flat brand colour, never a human tone.
fills: solid flat colour only. no gradient, no shading, no texture, no outline,
no drop shadow, no ambient occlusion, no lens flare, no depth of field.
background: one flat colour plus large geometric shapes running off canvas,
circles, arcs, quarter rounds, thick bars.
palette, use only these and nothing else: <HEXES>
motion: shapes cut and slide on hard eases, figures hold two or three poses,
no realistic in-betweens, no camera dolly, no parallax, no zoom. 24fps, clean loop.
absolutely no text, no letters, no numbers, no signage, no logo anywhere in frame.
```

Negative prompt, every time:

```
photoreal, 3d render, cinematic lighting, film grain, human skin tone, faces,
eyes, text, letters, numbers, watermark, live action, gradient, drop shadow
```

## The pipeline

Four steps. Step 2 costs cents, step 3 costs dollars, step 4 is free.

1. **Beat sheet.** Write the three beats and the caption for each. Show the user. Get a yes
   before spending anything.
2. **Keyframe.** Make one flat vector still with `google/gemini-3-pro-image` on OpenRouter,
   about a cent. This is where you iterate. Text to video invents a new palette every run;
   image to video inherits the keyframe's exact colours. Get the still right, then animate
   once.
3. **Render.** `bytedance/seedance-2.0`, image to video from the keyframe. The keyframe is
   pinned as **both** `first_frame` and `last_frame`, so the clip returns to where it
   started and loops with no visible cut.
4. **Burn.** Overlay the captions and the end card with the real brand font, scale to
   1080x1920, trim to length.

## The model

Default is `alibaba/wan-2.7`. Override per video with `"model"` in the spec, or per brand
with `"video_model"` in the brand file.

Three things this job needs, and they knock out most of the field:

1. **A last frame.** The loop comes from pinning one keyframe as both `first_frame` and
   `last_frame`. No last frame, no loop. This cuts Sora 2 Pro, Runway, Grok Imagine,
   Hailuo 2.3, Wan 2.6, and Happyhorse.
2. **A seed.** Without one, every re-render is a fresh roll and you cannot change a single
   clause and keep the take. This cuts Kling 3.0, Hailuo 3, and FLUX 3 Video.
3. **Nine seconds.** The whole Veo 3.1 family caps at 8.

What survives, priced for 9 seconds at 720p vertical with audio:

| model | seed | last frame | neg prompt | 9s cost, USD |
|---|---|---|---|---|
| **alibaba/wan-2.7** | yes | yes | **yes** | **0.90** |
| bytedance/seedance-1-5-pro | yes | yes | no | 0.47, or 0.23 mute |
| bytedance/seedance-2.0-mini | yes | yes | no | 0.68 |
| bytedance/seedance-2.0-fast | yes | yes | no | 0.82 |
| bytedance/seedance-2.0 | yes | yes | no | 1.37, measured |
| bytedance/seedance-2.5 | yes | yes | no | 2.08 |

Wan 2.7 wins on the thing that decides this style. It is the only one of them that takes a
**negative prompt**, and a negative prompt is the main lever against photoreal drift. Every
video model is trained to add light, depth, and texture. Flat vector is defined by what is
absent, so the ability to name what must not appear is worth more here than raw quality.
Reviewers also put Wan ahead on holding a drawn style through motion, where Seedance slides
towards a soft 2.5D look. Wan is cheaper than Seedance 2.0 as well.

The catch is that Wan favours the prompt over the frames when the two disagree. Describe a
motion that **returns**, like a cycle or a sway, never a one way exit, or it will fight the
pinned last frame and jump at the midpoint.

`bytedance/seedance-1-5-pro` is the budget pick at a third of the price, and mute it for
half of that again. Take it when you are shipping volume and the sound comes from TikTok
anyway.

Seedance is priced by video token, so the bill is pixels times frames times length:
`w * h * fps * seconds / 1024` tokens. Wan, Veo, and Kling bill by the second.

## Cost

| Step | Cost, USD |
|---|---|
| keyframe, gemini image | about 7 cents each, two or three is normal |
| render, wan-2.7, 720p, 9s | 0.90 |
| caption burn, local ffmpeg | 0 |

`gen` prints the balance before it submits. Check it yourself first when the budget is
thin, because a render that runs out of credit still costs the wait.

```bash
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/key
```

## Running it

```bash
node ~/.agents/skills/memphis-tok/vid.mjs key  <spec.json>   # keyframe, cents
node ~/.agents/skills/memphis-tok/vid.mjs gen  <spec.json>   # render, 1.53 usd at 9s/720p
node ~/.agents/skills/memphis-tok/vid.mjs burn <spec.json>   # captions, free
```

Everything lands in `out/` beside the spec. `OPENROUTER_API_KEY` comes from the
environment. Never write a key into this skill: `~/.agents` is a public repo.

## The spec file

One JSON file per video. Write it to the project, not to this skill.

```json
{
  "id": "hgc-bond",
  "brand": "hgc",
  "dur": 9,
  "resolution": "720p",
  "seed": 9,
  "shot": "one shot, camera locked. a figure stands at a tall flat archway...",
  "audio": "sound design only, soft paper whooshes and low pops, no voice, no music",
  "captions": [
    { "t": [0.0, 1.2], "label": "aug 2026", "line": "a us visitor visa\nnow costs *$15,000*" },
    { "t": [1.4, 6.0], "line": "it is a bond.\nyou get it back *only if you leave on time*." },
    { "t": [6.2, 7.6], "line": "most people\nnever claim it" }
  ],
  "endcard": "hogan and crown law"
}
```

- `brand` names a file in `brand/`. Add a new one by copying `brand/hgc.json`.
- `*stars*` wrap the phrase that turns brand green.
- `\n` is a hard line break. Break the line where a person would breathe.
- `label` is the small mono line above the caption. Leave it out on most cards.
- The end card is added automatically over the last 1.6 seconds.

## Sound

Set `generate_audio: true` and ask the prompt for sound design only, never a voice. A
generated voice sounds synthetic, and synthetic reads as a scam in the comments. Then add a
trending sound in the TikTok app at upload. Native trending audio is a ranking signal and
it is free. The burned-in captions carry the words, so the video works muted, which is how
most of the room watches.

## What kills these videos

- Text asked of the video model. It comes back as melted glyphs. Burn it in.
- Two ideas in nine seconds. Cut one.
- A logo in the first second. Nobody stays for a brand.
- A voiceover from the model.
- Realistic motion. Corporate memphis reads as snap and hold, not as animation.
- A hard end. Match the last frame to the first or lose the rewatch.
- Colours outside the palette. List the hexes and say "nothing else".

## After the render

Tell the user to upload in the TikTok app, not the web uploader, add a trending sound, and
put one search-shaped sentence in the description. The niche is searched, not only
browsed, so the description is a ranking surface.
