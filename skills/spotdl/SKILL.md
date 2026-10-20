---
name: spotdl
description: Download a Spotify song, playlist or album to local mp3 files with spotdl. Use when the user says spotdl, download this song from Spotify, get the mp3 of a Spotify link, or pastes an open.spotify.com URL and wants the audio file.
---

# spotdl

Installed with `pipx install spotdl` (4.5.2, 2026-10-20). Never pip. Needs ffmpeg (`/usr/bin/ffmpeg`). Check: `spotdl --version`.

Download one song into `~/music/spotdl`:

```bash
mkdir -p ~/music/spotdl && cd ~/music/spotdl && spotdl download "<spotify url>" --format mp3 --output "{artists} - {title}.{output-ext}" --print-errors
```

Playlist or album: same command with that URL. Add `--save-errors errors.txt` to keep the failed tracks.

Check the file is the full song:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "<file>"
```

The seconds should match the track length on Spotify. A far-off length means a wrong YouTube match; tell Ed, don't hand it over as done.

Traps (seen 2026-10-20):
- No Spotify key needed. Metadata lookup worked with the default credentials.
- Audio comes from a YouTube Music search, then falls back to YouTube after 3 empty tries. Slow first run is normal.
- Output was 128 kbps mp3 from the YouTube source. A higher `--bitrate` adds no real quality.
- `save --save-file` must end in `.spotdl`, else: `Save file has to end with .spotdl`.
- Personal use only. Spotify's terms and the song's copyright still apply.
