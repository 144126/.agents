---
name: know
description: Shared agent memory with local semantic recall. Use to record turn activity, save verified facts, replace outdated notes, recall current facts, or search note history.
---

# know

The append-only journal is authoritative. A Turso database indexes its notes and embeddings. Use the CLI for all live store operations; never hand-edit `~/.know` or open its database with another tool.

## Commands
- `know start [-n 18] "<request and intent>"`: session/turn start in one call. Prints the 18 newest notes from before this call, then saves the argument as an activity note (`saved #N`). Takes `--kind` and `--replaces` like `note`.
- `know note --kind activity "<request or outcome>"`: record turn activity. Keep the required start/end writes; save lasting facts separately.
- `know note "<verified fact>"`: save one fact, at most 280 chars.
- `know note --replaces 12 --replaces 18 "<verified replacement>"`: retire named notes from factual recall. Old notes remain in history. Name only notes this statement actually replaces.
- `know ask [-n 9] [--min-score 0.60] "<question>"`: search current facts. Matches need both semantic similarity and a meaningful query word in the note. Results show cosine similarity, not a probability of correctness. It reports no strong match when no candidate passes.
- `know ask --semantic-only "<paraphrase>"`: allow matches without shared words. Use this for broader discovery or a paraphrase the default search misses; lower `--min-score` explicitly when needed.
- `know wake [-n 18]`: recent notes in time order, including activity and replaced notes, with labels.
- `know grep [-n 18] <regex>`: search all note history, case ignored; activity and replaced notes are labeled.
- `know doctor [--check-vectors]`: validate the complete journal and index, replay missing notes, and check index integrity. The optional check compares sample embeddings with the current model, allowing for quantization variation.
- `know rebuild`: validate the journal, build and check a replacement index, then install it. The journal stays unchanged; embeddings regenerate on the next `ask`.
- `know import <file>`: validate a legacy or JSON-lines journal and import it into an empty store. Conflicting IDs and incomplete records are refused; the source stays unchanged.
- `skills/know/bin/setup`: build the venv and fetch the model. Safe to run again.

## Files
- `~/.know/log`: journal. New records use JSON fields `i` (ID), `d` (date), `t` (text), `k` (`a` activity, `f` fact), `x` (replaced IDs). Legacy `#id date text` records remain readable as facts; old records are never rewritten.
- `~/.know/db`: disposable index, table `n(i, d, t, e)`. `~/.know/lock`: exclusive CLI lock. `KNOW_DIR` relocates the store for isolated tests.
- `~/.venvs/know`: Python 3.11, dependencies pinned in `requirements.txt`. `~/models/arctic-embed-xs`: shared ONNX model, 384 dims (23 MB).

## Traps
- Search similarity does not prove a fact is current or true. Check current files or authoritative sources before acting. A miss means verify elsewhere, then record what was verified.
- Old entries default to facts for compatibility. Explicitly replace observed stale notes or retire reviewed activity entries with an activity record; do not classify or delete old notes in bulk by guessed wording.
- `note` syncs the journal before updating the index. If index insertion fails, it reports the saved ID; the next command replays it before allocating another ID. A journal write/sync failure reports uncertain persistence. Run `know doctor` to confirm recovery before retrying the same fact.
- `ask` embeds only current facts without embeddings, under the lock. The first query after a rebuild can take longer. Activity gets no embeddings.

## Repair
- Start with `know doctor`. For an index mismatch or corruption with a valid journal, use `know rebuild`, then `know doctor`.
- A conflicting ID, malformed record, or incomplete final line stops recovery before replay. Preserve the journal and report the exact location; never repair it by silently discarding records or deleting store files.
- Regression checks: `PYTHONDONTWRITEBYTECODE=1 ~/.venvs/know/bin/python ~/.agents/skills/know/tests.py`. They use temporary stores and the shared model.
