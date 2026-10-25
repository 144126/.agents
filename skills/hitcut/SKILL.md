---
name: hitcut
description: Hitcut, the local timeline for hit tracks (JSONL) over a song. Use when opening or editing a song's hits, starting the hitcut dev server, or finding where transcriptions and hit files live.
---

# hitcut

Home for songs, transcriptions and hit files: `~/AUD/songs/<song>/`. One folder per song, named `Artist - Title`. Each folder holds the audio plus every `.jsonl` track for that song.

```
~/AUD/songs/EsDeeKid - Phantom/EsDeeKid, Rico Ace - Phantom.mp3
~/AUD/songs/EsDeeKid - Phantom/hits.jsonl
```

Start: `~/i/hitcut`, `./serve` (= `pnpm dev`) on `http://127.0.0.1:8009`. Check first: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8009/`. Log: `~/i/hitcut/.log`.

`./serve` writes no log itself. Start it with: `cd ~/i/hitcut && setsid nohup ./serve > .log 2>&1 < /dev/null &`. Then wait for HTTP 200 on `127.0.0.1:8009` before opening the browser.

Audio from a YouTube URL: `yt-dlp --no-cache-dir -f 251 -o '~/AUD/songs/<Artist - Title>/<Title>.%(ext)s' <url>`. Format 251 is webm, so no transcode is needed.

Open a song in the browser (URL-encode spaces as `%20`):

```bash
xdg-open "http://127.0.0.1:8009/?path=/home/ed/AUD/songs/EsDeeKid%20-%20Phantom"
```

Traps:
- Only top-level files load. A `.jsonl` in a subfolder is ignored.
- A symlink to a file outside the song folder returns 403. Copy the file in instead.
- Existing audio is read-only. Only `.jsonl` tracks are written. `n` makes a new track.
- Track name = file name. `hits.jsonl` shows as `hits`.
- 2026-10-20: 16 song folders were copied into `~/AUD/songs/` from the old scattered hitcut projects. Originals were left in place. Byte-identical duplicates were skipped.
- `Vite environment "nitro" is unavailable`: page opened before the dev server finished starting. Wait until `curl` of the URL returns 200 without `NitroViteError`, then open it.
