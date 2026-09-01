---
name: research
description: Quote-audited web research — search, scrape, extract, gate, ledger. Use when answer must be traceable to verbatim quotes.
---

# Research — audited ledger

Search → scrape → LLM extract → quote-gate → `~/search/<slug>.md`.
Gated ledger is the truth. Synthesis is separate and flagged unverified.

## What it proves

- Every `SINGLE` claim has verbatim `quote` found in the source page (whitespace-normalized).
- Every number/date in `claim` is in that `quote`.
- `CORROBORATED` means byte-identical claim wording on ≥2 registrable domains (rare — usually `None`).
- It does **not** prove truth, no paraphrase detection, no source quality rank.

## Output

- `~/search/<slug>.md` — gated ledger (Corroborated / Single-source / Unchecked + Sources table + Process audit).
- `~/search/<slug>/synthesis.md` — post-search synthesis **only if `--think`** (flagged UNVERIFIED, not gated).
- Work dir `~/search/<slug>/` — `meta.json`, `state.json`, `search-*.json`, `pages/*.txt`, `extracts/*.json`, `claims.*.jsonl`.
- Think dir `~/think/<slug>-research-*.r|*.conclusions.md|*.md` — only if `--think`.

## Usage

```bash
# ask (default: no thinking, ~10 searches, ~15-20 pages, no synthesis)
~/.agents/skills/research/bin/research.ts "<question>"

# with thinking (adds ~10 pre + ~10 post angles, synthesis.md, costs ~5x)
~/.agents/skills/research/bin/research.ts "<question>" --think

# choose model / reasoning
~/.agents/skills/research/bin/research.ts "<question>" --model openrouter/z-ai/glm-5.3-flash --reasoning high

# explicit search angles (skip pre-thinking query derivation)
~/.agents/skills/research/bin/research.ts "<question>" --angle "q1" --angle "q2"

# resume / explicit slug
~/.agents/skills/research/bin/research.ts --resume <slug>
~/.agents/skills/research/bin/research.ts "<question>" --slug my-slug

# verbose
~/.agents/skills/research/bin/research.ts "<question>" --verbose
```

## Model

Default `openrouter/z-ai/glm-5.3-flash`. Override via `RESEARCH_MODEL=provider/id` or `--model`. Providers: `openrouter`, `amazon-bedrock-mantle`.

## Cost / time

- Default (no `--think`): ~20 LLM calls (1 query-derivation + ~15 extracts), ~2-4 min, ~$0.30-0.80.
- With `--think`: +20 thinking calls + 1 post-angle gen + synthesis, ~8-12 min, ~$1.50-3.

## Resume

State is `~/search/<slug>/state.json`. Re-running same question reuses `slug` and skips done `search:*` / `page:*`. Use `--resume <slug>` to resume unambiguously; bare `<slug>` still works if it matches an existing work dir but prefers explicit flag.

## Limits

- No source quality ranking, no dedup of paraphrased syndication, Corroborated rarely fires.
- Synthesis (if any) is LLM summary, not gated — read ledger for audit.

## Relation

- `condense` — single text → gated facts (no web).
- `research` — web → gated ledger (this skill).
