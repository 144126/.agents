---
name: muscriptor
description: Transcribe a song's drums (or other instruments) to timed hits with MuScriptor for beat-synced edits. Use when cutting video to kicks, snares or any instrument hit.
---

# muscriptor

Local CPU, medium model, `~/.venvs/audio8`. Large OOMs locally. Lightning auth failed 2026-11-04 ("Please run `lightning login`"): Ed must log in again before any remote large run.

```bash
# 1.2 GB into $HF_HOME; xet downloads stall, so disable xet
HF_HUB_DISABLE_XET=1 ~/.venvs/audio8/bin/python -c "from huggingface_hub import snapshot_download as s; s('MuScriptor/muscriptor-medium')"
ffmpeg -ss <start> -t <len> -i song.webm win.wav   # only the section you cut; add <start> back to every time
HF_HUB_OFFLINE=1 ~/.venvs/audio8/bin/muscriptor transcribe win.wav --model medium --device cpu --dtype float32 --cfg-coef 1 --instruments drums --format jsonl -o drums.jsonl
```

- Events: `{"type": "start", "pitch": 36, "start_time": 5.14, ...}` plus `end` events. Drums: 35/36 kick, 37-40 snare, 42/46 hats. 808 shows as electric_bass, not drums.
- Speed: a 60 s window takes about 4 min on the i7-8565U with `--instruments drums`.
- Trap: on CPU, a whole 5 s chunk can come back with zero events, which looks like a drum break. Find gaps longer than 2 beats with no event of any pitch. Re-run windows offset by about 2.5 s and take the union per pitch within 50 ms.
- Keep the merged track at `~/AUD/songs/<Artist - Title>/drums.jsonl` in song time (hitcut reads it). Then delete the model folder.
