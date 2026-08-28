---
name: tri-research
description: Three-phase audited research — pre-think, condense-search, post-think. Minimal by default (9/9/9), thorough opt-in (18/18/18). Use when user wants deep/thorough research, investigation from all angles, or says tri-research, thorough research, full spectrum, research deeply.
user-invocable: true
argument-hint: <topic> [--quick] [--thorough] [--pre N] [--turns N] [--post N] [--no-audit]
---

# tri-research — think, search, think (minimal by default)

54-angle rethink on 2026-08-27 fixed the first version's waste. First run used 36 searches + 31 extracts for 57 verified claims in ~12 min. 60% was redundant.

## Defaults (necessity rule)

| Mode | Pre | Turns | Post | When |
|------|-----|-------|------|------|
| minimal (default) | 9 | 9 | 9 | 90% of topics, ~4 min, ~15 verified claims |
| --quick | 4 | 4 | 4 | lookup + light audit |
| --thorough / --full | 18 | 18 | 18 | deep audit, opt-in only |
| custom | --pre N --turns N --post N | | | 1..54, multiples of 9 preferred |

Add --no-audit to skip phase 2 gating and do think+search->synthesis only.

## One r file, not two

```bash
slug=$(echo "$topic" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]\+/-/g' | cut -c1-48)
mkdir -p ~/think
r9 init ~/think/${slug}.r --angles 18
# edit ~/think/${slug}.r to have two groups:
# "_" = topic + constraints + ledger path hint
# c.pre.a01..a09 = how to research (vocab, opposite, adjacent, data, who-benefits, philosophy)
# c.post.a01..a09 = synthesis angles (placement, second-order, weakest evidence, contrary)
# For --thorough, init --angles 36 and split 18/18.
```

## Phase 1 — Pre-think (minimal: 3 searches, not 18)

Don't do 18 searches. Three batched searches cover 80%:

```bash
firecrawl search "floating chatbot widget UX best practices vocab insiders vs critics" --limit 10 --json -o "/tmp/${slug}-pre-01.json" &
firecrawl search "why floating chat widgets annoy increase bounce when not to use" --limit 10 --json -o "/tmp/${slug}-pre-02.json" &
firecrawl search "adjacent patterns FAB toast modal bottom sheet calm technology" --limit 10 --json -o "/tmp/${slug}-pre-03.json" & wait
# read each fully, synthesize 5-bullet pre conclusion
# for --thorough, run 18 as before; reuse any fetched URLs (>1k) as phase-2 seeds deduped by normalized URL
```

Rule: if topic is simple and `firecrawl search` would answer, skip tri-research entirely.

## Phase 2 — Research (batch gate, early stop, dedupe)

```bash
# 1 — search, 9 turns minimal (12 if verified <15, 18 if --thorough)
# each turn distinct angle: direct, opposite, adjacent, who-benefits, data, contrarian
firecrawl search "<angle 1>" --limit 10 --json -o "/tmp/${slug}-01.json" &
# ... up to N; run in parallel batches

# early stop: after 9, check verified count; stop if >=20 verified from >=8 domains and >=1 contrary

# 2 — collect, deduped
~/.agents/skills/condense-search/bin/cnd init "<subject>" --slug $slug
# normalize URLs (strip utm, lower host, trim /) before fetching, dedupe pre+main
# fetch with 20s timeout, retry once with --mode fast, skip failures (fetched=no)
firecrawl scrape "<url1>" -o /tmp/p1.md &
firecrawl scrape "<url2>" -o /tmp/p2.md &
wait
~/.agents/skills/condense-search/bin/cnd add-source $slug --url <url1> --title "<title>" --file /tmp/p1.md

# 3 — extract: one load-bearing claim per page, not titles. Smoke test first.
# test: 1 search + 2 extracts + gate; if verified==0 fix template before launching rest
# for each page write ~/search/$slug/extracts/<pid>.json per references/extract_prompt.md
# require quote_in_text(page_text) pre-check; reject title clones (must have verb and >=8 words)
# skip junk: if txt contains "Stars:" and "Forks:" or txt_len <800, one claim or []

# 4 — gate batched
~/.agents/skills/condense-search/bin/cnd ingest-extract $slug ~/search/$slug/extracts/*.json
~/.agents/skills/condense-search/bin/cnd gate $slug
~/.agents/skills/condense-search/bin/cnd write $slug --question "<original>"
# publishes ~/search/$slug.md
```

If --no-audit, skip cnd and just synthesize from search excerpts.

## Phase 3 — Post-think (read gated json, not just md)

```bash
# before starting, read ~/search/$slug/claims.gated.jsonl and ~/search/$slug.md fully
r9 ~/think/${slug}.r  # walks pre then post leaves (one file)
# for each leaf: think deep, steelman both sides, cite source_url per bullet
# dedup after thinking: read ~/think/${slug}.conclusions.md only then, append new bullets
# when r9 prints 0:
r9 ~/think/${slug}.r --write  # publishes ~/think/${slug}.md
```

Final answer is ~/think/${slug}.md grounded in ~/search/${slug}.md. Append appendix of top 5 claim — "quote" pairs and a Weakest Evidence section (3 least supported bullets) per quality gates.

## Outputs (minimal)

- ~/search/<slug>.md
- ~/think/<slug>.md
Delete /tmp/pre-*.json and /tmp/p-*.md after write unless --verbose. No duplicate .conclusions.md needed.

## Robustness fixes (from 54-angle review)

- Subagents: don't spawn 31 parallel; do extracts sequentially or 5 per subagent.
- Mark done via r9 <file> <path> not manual json edit; use --skip for junk.
- Normalize URLs before fetch; reuse pre URLs as seeds.
- Local gate pre-check prevents paraphrased quotes that will be rejected.
- Adaptive turns: 9 minimal, escalate only if verified <15 or corroborated==0.

## Philosophy

Keep verbatim quote audit in every mode — minimal cuts searches, not rigor. North Star is verified high-value claims per minute (target 3.75/min at 1/3 cost). If `firecrawl search` suffices, don't use tri-research. Applied 54-angle rethink: ~/think/tri-research-improve.md

## Enforcement — r9 is mandatory for pre and post

`tri-research` is two `r9` runs. Skipping `r9` and writing `~/think/<slug>.md` directly is forbidden.

Required:
```bash
r9 init ~/think/<slug>.r --angles 18   # or 36 for --thorough, split pre/post
# then for pre leaves:
r9 ~/think/<slug>.r ; # think on that pre leaf only, append to conclusions.md; r9 ~/think/<slug>.r <path> ; repeat
# then for post leaves (read ~/search/<slug>.md + claims.gated.jsonl first):
# same walk, then r9 ~/think/<slug>.r --write
```
Gate: `r9 -l` must show `d:1` for every pre+post leaf, `conclusions.md` must be leaf-wise appended, and `--write` must have been run. Bulk-filled think files without `r9` marks are rejected.
