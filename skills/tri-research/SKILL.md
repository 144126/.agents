---
name: tri-research
description: Three-phase audited research — rethink, condense-search, rethink. Minimal by default (9/9/9), thorough opt-in (18/18/18). Use when user wants deep/thorough research, investigation from all angles, or says tri-research, thorough research, full spectrum, research deeply.
user-invocable: true
argument-hint: <topic> [--quick] [--thorough] [--pre N] [--turns N] [--post N] [--no-audit]
---

# tri-research

Think, search, think. If a single `firecrawl search` would answer, skip this skill.

| Mode | Pre | Turns | Post |
|------|-----|-------|------|
| default | 9 | 9 | 9 |
| --quick | 4 | 4 | 4 |
| --thorough | 18 | 18 | 18 |

`--no-audit` skips the quote gate. Load `rethink` and `condense-search` and follow those skills. Do not call `r9` yourself.

## 1 — pre-think

```bash
rethink "how to research: <topic>" <pre>
```

Summarize `~/think/<slug>.conclusions.md` only. Use those bullets as the search angles.

## 2 — search

Follow `condense-search` for `<turns>` angles. `--no-audit`: search and scrape, then synthesize from excerpts — no `cnd`.

Early stop after 9 turns if you already have ≥20 verified claims from ≥8 domains and ≥1 contrary.

## 3 — post-think

Read `~/search/<slug>.md` (and `claims.gated.jsonl` if it exists). Then:

```bash
rethink "synthesize: <topic>  (ground every bullet in ~/search/<slug>.md)" <post>
```

Summarize that conclusions file only. That is the answer. Cite source URLs. Add the 3 weakest bullets at the end.

## Outputs

- `~/search/<slug>.md`
- the two `~/think/<slug>.conclusions.md` files rethink wrote
