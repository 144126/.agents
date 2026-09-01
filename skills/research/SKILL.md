---
name: research
description: Quote-audited web research — search, scrape, extract, gate, ledger. Use when answer must be traceable to verbatim quotes.
---

# Research — audited ledger

Search → scrape → extract → gate → `~/search/<slug>.md`. No thinking.

## What it proves

- Every `SINGLE` claim has verbatim quote found in source (whitespace-normalized).
- Every number/date in claim is in that quote.
- `CORROBORATED` is byte-identical wording on ≥2 domains (rare — usually None).
- Does not prove truth, no paraphrase detection.

## Output

- `~/search/<slug>.md` — ledger (Corroborated / Single / Unchecked + Sources + audit).
- Work dir `~/search/<slug>/` — `meta.json`, `state.json`, `search-*.json`, `pages/*.txt`, `extracts/*.json`, `claims.*.jsonl`.

## Usage

```bash
~/.agents/skills/research/bin/research.ts "<question>"
~/.agents/skills/research/bin/research.ts "<question>" --angle "q1" --angle "q2"
~/.agents/skills/research/bin/research.ts "<question>" --slug my-slug
~/.agents/skills/research/bin/research.ts --resume <slug>
~/.agents/skills/research/bin/research.ts "<question>" --model openrouter/z-ai/glm-5.3-flash --verbose
```

No `--think` — use `rethink` skill for synthesis.

## Model

Default `openrouter/z-ai/glm-5.3-flash` via `RESEARCH_MODEL=provider/id` or `--model`.

## Cost

- ~1 LLM for 6 queries + 1 per page (cap 10 pages) = ~11 calls, ~90s, ~$0.30.

## Resume

`state.json` skips done `search:*`/`page:*`. Use `--resume` explicit; bare slug still resumes with warning.
