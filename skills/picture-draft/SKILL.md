---
name: picture-draft
description: Make a picture by drafting SVG, then Muse Spark Image via OpenRouter (3-call ceiling). Use when the user wants a picture, image, illustration, poster, scene, or visual.
---

# Picture Draft

SVG is the cheap wireframe. Muse is the expensive render. Ceiling 3 Muse calls — stop early.

## Do

1. If the request is under 15 words, add 2–3 concrete visual details (style, light, composition). Else use it verbatim.
2. Write `.picture-draft/<yyyy-mm-dd-slug>/draft.svg`. Blocks for regions, one focal shape, flat palette. No textures.
3. Render, read the PNG, fix the SVG. Repeat until the composition is right.
   ```bash
   python3 ~/.agents/skills/picture-draft/scripts/picture.py render draft.svg draft.png
   ```
4. Generate (needs `draft.png`):
   ```bash
   python3 ~/.agents/skills/picture-draft/scripts/picture.py generate \
     --prompt "..." --ref draft.png --out output-01.png
   ```
5. Read the image. Good → stop. Else one of:
   - small fix: `picture.py edit --image output-01.png --prompt "change X, keep the rest" --out output-02.png`
   - missed brief: `picture.py generate --prompt "..." --ref draft.png --out output-02.png`
6. One more of those if needed. At 3/3, stop and present the best.

No mid-flow questions. Deliver the image. Budget stays internal.

`OPENROUTER_API_KEY` required. Model `meta/muse-spark-1.2`. Failed HTTP does not count.
