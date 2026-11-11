---
name: know
description: Agent memory in one Turso db with local semantic recall. Use to read recent notes, save a note, or find old notes by meaning or by exact words.
---

# know

Memory for all agents. One Turso db (the Rust SQLite rewrite, PyPI `pyturso`) holds each note and its vector. It replaced OptMem on 2026-11-11.

## Commands
- `know wake [-n 18]`: the newest notes.
- `know note "<text>"`: save one note, at most 280 chars.
- `know ask [-n 9] "<question>"`: the notes nearest in meaning.
- `know grep [-n 18] <regex>`: notes whose line `#<id> <date> <text>` matches, case ignored.
- `know import <file>`: load `#<id> <date> <text>` lines into an empty store.
- `skills/know/bin/setup`: build the venv and fetch the model. Safe to run again.

## Files
- `~/.know/db`: table `n(i, d, t, e)`. `~/.know/log`: journal, one line per note. `~/.know/lock`: flock. `KNOW_DIR` moves all three.
- `~/.venvs/know`: Python 3.11, pins in `requirements.txt` (168 MB). `~/models/arctic-embed-xs`: ONNX model, 384 dims (23 MB).

## Traps
- Turso rejects a second process on the same file. Each command holds `~/.know/lock`. Do not open `~/.know/db` with another tool.
- Turso has no vector index: `ask` is a full scan, 0.45 s at 2025 notes, most of it model load.
- `note` does not embed. The next `ask` embeds the notes that have no vector (38 s for 2025 notes).
- Turso is pre-1.0. The journal is written first, so it holds every note.
- `wake` takes 0.10 s, `note` 0.11 s.
- Turso keeps its file lock until the process exits, a few ms after the flock is dropped: store() retries the open for 9 s.

## Repair
- Rebuild the db, or re-embed after a model change: `rm ~/.know/db*`, then `know import ~/.know/log`, then one `know ask`.
