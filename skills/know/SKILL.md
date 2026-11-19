---
name: know
description: Shared agent memory with local semantic recall, stored as rope lines. Use to record turn activity, save verified facts, replace outdated notes, recall current facts, or search note history.
---

# know

Agents' memory and Ed's rope notes are one store: `~/.know/rope.db`, rope's Turso file. A note is a rope line: facts sit under `know › facts`, activity under `know › activity › <date>`. Every other rope line counts as a fact too, so agents see Ed's notes and Ed sees theirs in rope (http://127.0.0.1:9099). Code: `~/i/me/rope/src/lib/store/know.ts`, CLI `~/i/me/rope/bin/know.ts` (on PATH as `know`).

## Commands
- `know me [-n 18] ["<turn activity>"]`: print the 18 newest lines, then save the optional text as activity (`saved #N`). Takes `--kind` and `--replaces` like `note`. Run with the request and intent at the start of every turn and the outcome, decisions, and open work at the end.
- `know note --kind activity "<activity>"`: record other activity; save lasting facts separately.
- `know note "<verified fact>"`: save one fact, at most 280 chars.
- `know note --under todo [--under wsp] "<text>"`: file a note under the rope line with that text instead of `facts` (case ignored; newest edit wins when names repeat; a missing line is made). One note can sit under many lines. Use when Ed says "save this under X".
- `know ls <line>`: the lines under that line, in rope's order.
- `know note --replaces 12 --replaces 18 "<verified replacement>"`: marks the named notes done, so `ask` skips them; `grep` labels them `[replaced]`. Name only notes this statement actually replaces.
- `know ask [-n 9] "<question>"`: search current facts by meaning. A match needs similarity ≥ 0.4 and a meaningful query word in the note. Similarity is not a probability of correctness.
- `know grep [-n 18] <regex>`: search every live line, case ignored; activity and replaced notes are labeled.
- `know doctor`: integrity check and counts.

## How it works
- The rope server (`~/i/me/rope/bin/run`, started at sway login) holds Turso's exclusive file lock, so `know` posts to `127.0.0.1:9099/api/know`. When the server is down, `know` opens the file itself, and waits up to ~10 s if it is starting.
- Meaning: blink-8M int8 static embeddings (`~/models/static-int8/blink-8M-int8.safetensors` + `~/models/blink-8M/tokenizer.json`), plain JS, no ML runtime. Vectors live in rope's `l.e`; a model change clears them, and they refill on the next `ask` or within a second on the server.
- Notes imported from the old journal kept their ids (0-3254); new ones count on from the highest id under 1e12. Lines made in rope have long time-based ids.
- `~/.know/log` is the old append-only journal, frozen 2026-11-19 after the import; nothing writes it now.

## Traps
- Search similarity does not prove a fact is current or true. Check current files or authoritative sources before acting. A miss means verify elsewhere, then record what was verified.
- Never open `~/.know/rope.db` with another tool while the server runs (lock error); use `know` or rope's HTTP API.
- Marking a line done in rope also retires it from `ask`.
