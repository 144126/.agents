---
name: condense
description: >-
  Condense a single block of text or a text file into a series of
  quote-anchored facts. No web, no search. The binary gates every claim against
  the source text (verbatim quote required; numbers must sit in the quote;
  negation polarity must match) so extracted "facts" stay honest. Trigger on
  "condense", "condense this text", "extract facts from this", "fact list from
  a passage". For merging web search results into an audited ledger, use the
  condense-search skill instead.
---

# Condense — single-text fact extractor

You do **not** launder a passage into facts in chat. Extract quote-anchored
claims following [references/extract_prompt.md](references/extract_prompt.md).

<!-- GATE BINARY — commented out for simplicity
## Binary

```bash
# always on PATH for this skill:
~/.agents/skills/condense/bin/condense
# or:
export PATH="$HOME/.agents/skills/condense/bin:$PATH"
```

Offline. No API keys, no network.
-->

## Procedure

### 1 — read the prompt

Read `references/extract_prompt.md` to understand the extraction format.
Draw every `quote` verbatim from the source text.

### 2 — extract

Follow the extract prompt. Write claims, each with a verbatim `quote` from
the source text (≤40 words). Rules: no invented numbers; empty claims OK;
keep hedges that change strength/scope; every number/date in `claim` must
also appear in `quote`.

### 3 — emit

Output facts as:

```
> <claim> — "<verbatim quote>"
```

If a claim's quote cannot be found verbatim in the source, put it in a
**Rejected** section instead. The goal is a series of quote-anchored facts,
not a summary — the quotes let a reader audit each claim against the source.

<!-- GATE CHECK — commented out for simplicity
### 3 — gate

```bash
condense gate --source path/to/source.txt --claims facts.json
# or inline source:
condense gate --text "…" --claims facts.json --out facts.md
```

Does:
- quote substring check (exact / whitespace-normalized only) -> reject if missing
- number/date containment (every figure in `claim` must be in the quote window)
- negation polarity (quote and claim must agree on polarity)

Prints a facts markdown: each fact as `> <claim> — "<quote>"`, plus a
**Rejected** section for any claim whose quote was not found verbatim. With
`--jsonl` it also writes the gated claims (with `quote_found`, `number_gate_fail`,
`polarity_fail`); with `--out` it writes the markdown to a file.
-->

<!-- STATUS — commented out for simplicity
## Status

A single source has no independence, so this skill does not assign
CORROBORATED/AUTHORIZED. It reports **fact** (quote found, gates pass) or
**rejected** (quote missing / numbers absent / polarity mismatch). One source =
one unit; corroboration across sources is the job of condense-search.
-->

## Anti-patterns

1. Chat-only condense without verifying quotes against source
2. Calling a marketing sentence a fact after paraphrase
3. Inventing quotes/citations
4. A quote that states a *different* number than the claim
5. Letting a non-verbatim match through

## Relation

- **condense-search**: web search -> fetch -> extract -> gate -> audited ledger
- **condense**: one text block -> quote-anchored facts (this skill)
