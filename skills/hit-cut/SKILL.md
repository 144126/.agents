---
name: hit-cut
description: Alternate two pics on every kick/snare hit for 18s vid. Use when syncing pics to drum hits, kick/snare cuts, or 18s hit-cut video.
---

# hit-cut

18s vid: 2 pics x kick(36) + snare(38,40) hits, alternating.

```bash
ffmpeg -y -i song.mp3 -ss 60 -t 18 -c copy clip.mp3
```

```python
# muscriptor lives at ~/i/muscriptor/.venv — use ~/i/muscriptor/.venv/bin/python (has HF_TOKEN, weights gated at huggingface.co/MuScriptor/muscriptor-large)
from muscriptor import TranscriptionModel
m=TranscriptionModel.load_model("medium",device="cpu") # weights_path="large" for 1.4B if needed
hits=[e.start_time for e in m.transcribe("clip.mp3",instruments=["drums"]) if e.__class__.__name__=="NoteStartEvent" and e.pitch in (36,38,40)]
times=[0]+hits+[18] # -> segments times[i]:times[i+1]
```

```bash
# per segment: ffmpeg -loop 1 -i picA/B -t dur -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,scale=8000:-1,zoompan=z='min(zoom+0.0015,1.12)':d=1:s=1280x720:fps=30" -r 30 clip.mp4
# concat: printf "file 'clip_%03d.mp4'\n" > list.txt; ffmpeg -f concat -i list.txt -c copy vid.mp4
# mux: ffmpeg -i vid.mp4 -i clip.mp3 -c:v copy -c:a aac -shortest out.mp4
```

pics: last 2 `~/Downloads/*.webp` by `ls -t`, song: last `~/Downloads/*.mp3`.
