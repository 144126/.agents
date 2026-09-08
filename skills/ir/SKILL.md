---
name: ir
description: Make a picture by drafting SVG, super grids from video, or Blender blockout, then (if the user chose AI) one Muse Spark Image render. Use when the user wants a picture, image, illustration, poster, or shot blocking from video. Not for a video, animation, or blender-only 3d model.
---

# ir

SVG is the wireframe. Muse is the optional render. Two modes, user picks.

## Mode rule

The request must say AI or not ("AI", "with AI" vs "SVG only", "no AI"). If it doesn't say, ask the user explicitly — "AI render or SVG only?" — and do nothing else until they answer. Never guess.

## Do

1. If the request is under 15 words, add 2–3 concrete visual details (style, light, composition). Else use it verbatim.
2. Write `.picture-draft/<yyyy-mm-dd-slug>/draft.svg`. Blocks for regions, one focal shape, flat palette. No textures. If a context image exists — the previous shot's final frame in a sequence — read it first and carry over its palette, lighting, character design, and any elements that should persist.
2a. Draft source — SVG default, Blender or super optional. If the user says "blender", "3d blockout", "blockout", or `BLENDER=1`:
   - Build `.picture-draft/<slug>/blockout.blend` with <20 primitives only (plane/cube/sphere/cylinder), each a distinct vivid `diffuse_color` per `blender-cinematic-blockout` palette (e.g. Hero RED 0.95,0.15,0.18; Tower STEEL BLUE 0.30,0.35,0.42; Ground BEIGE 0.88,0.82,0.68). Lock `scene.camera` with `TRACK_TO` + `focus_distance`.
   - Render headless Workbench raw to `draft.png` (1024x1024, `BLENDER_WORKBENCH` + `FLAT` + `MATERIAL`): `python3 ~/.agents/skills/ir/scripts/picture.py blender-render blockout.blend draft.png`. Verify via `read` after one move. Write `.picture-draft/<slug>/prompt-map.txt` with one line per color: `RED cube IS Hero_Girl — ...` and paste that legend verbatim into the Muse prompt.
   - Else use SVG path. `draft.png` is the contract either way; 1-call ceiling and chaining are identical.
2b. If the user says "super", "supers", "video blockout", or gives a video to block shots from:
   - Run `python3 ~/.agents/skills/super/super.py <video> [start_sec] [dur_sec] .picture-draft/<slug>/supers`.
   - Each `supers/super_NN.png` is one shot layout (all frames in that second). Use the shot's super as the layout draft in place of `draft.png` in steps 3-5.
3. Render, read the PNG, fix the draft. Repeat until the composition is right.
   ```bash
   python3 ~/.agents/skills/ir/scripts/picture.py render draft.svg draft.png        # SVG draft
   python3 ~/.agents/skills/ir/scripts/picture.py blender-render blockout.blend draft.png  # Blender draft
   ```
4. **SVG only**: this render is the picture. Deliver it. Done.
5. **AI**: generate once (needs `draft.png`). One Muse call, ceiling 1. `--ref` is repeatable — when the picture continues a sequence, pass the previous shot's final frame as an extra ref and label every image in the prompt:
   - SVG draft: "the previous shot's final frame (first/left reference) — match its painted texture, palette, lighting, and character design exactly; the SVG layout draft (second/right reference) — follow its composition"
   - Blender draft: "the previous shot's final frame (first/left reference) — match its painted texture, palette, lighting, and character design exactly; the Blender Workbench blockout (second/right reference) — flat distinct colors, unlit — follow its camera, parallax and layout but replace flat colors with photoreal texture per legend: <paste prompt-map.txt lines>" The script sends multiple refs as an image array; if the model only takes one, they arrive composited side by side in ref order.
   ```bash
   python3 ~/.agents/skills/ir/scripts/picture.py generate \
     --prompt "..." --ref prev-shot.png --ref draft.png --out output-01.png
   ```
6. Read the image and present it. No retries, no edits — one Muse call only.

`OPENROUTER_API_KEY` required for AI mode only. Model `meta/muse-image` via `POST /api/v1/images`. Failed HTTP does not count.
