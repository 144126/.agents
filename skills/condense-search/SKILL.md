---
name: condense-search
description: >-
  Truth-seeking condense of live web results into an audited claim ledger:
  adaptive dual-channel sampling, quote-anchored extraction,
  deterministic quote/echo/numeric gates, graded status (no "settled"), vendor
  quarantine, process audit. Trigger on "cnd", "condense-search", or whenever the
  user wants search results merged into a clean honest fact-first document —
  "search and condense", "fact list from the web", "what do sources actually say".
  Prefer over naive summarization when accuracy matters more than speed.
  For condensing a single text block or file (no web), use the `condense` skill.
---

# Condense-search — web fact ledger

You do **not** launder web pages into facts in chat. Search the web, fetch
pages, extract quote-bound claims per page, and compile into an audited
ledger.

<!-- CLAIM CLASS & CHANNEL SPLIT — commented out for simplicity
## Inputs

- **query** / subject from user  
- optional `n<number>` budget (default 10)  
- claim class: `spec` | `efficacy` | `lived` | `default`

Channel split (enforced in `cnd init` meta):

| class | warrant | outside | adversarial |
|-------|---------|---------|-------------|
| spec | 70% | 20% | 10% |
| efficacy | 40% | 40% | 20% |
| lived | 30% | 50% | 20% |
| default | 45% | 40% | 15% |
-->

<!-- DISK CONTRACT — commented out for simplicity
## Disk contract

```
~/search/<slug>/           # work dir (orchestrator / cnd only)
  meta.json
  queries.jsonl
  sources.jsonl
  pages/<id>.txt           # full cleaned body
  pages/<id>.meta.json
  extracts/<id>.json
  claims.raw.jsonl
  claims.gated.jsonl
  clusters.jsonl
  ledger.md

~/search/<slug>.md         # published ledger
~/search/<slug>.claims.jsonl
~/search/<slug>.sources.jsonl
```

**Subagents never write `~/search/`.** They return extract JSON only.
Orchestrator runs `cnd ingest-extract`.
-->

## Procedure

### 1 — search

Search the web for the topic with whatever search tool is available in this
environment (built-in web search, an MCP search server, a CLI runner — no
specific provider is required). Use queries from different angles — proponents,
critics, independent sources — so you get a balanced picture.

### 2 — fetch

Pull the full text of the most relevant pages. For PDFs, extract text content.

### 3 — extract

For each page, extract quote-anchored claims following
`references/extract_prompt.md`. Every claim needs:
- A verbatim `quote` (≤40 words) from the page
- The `claim` text stating what the quote supports
- No invented numbers; keep hedges that change strength/scope
- Every number/date in `claim` must appear in `quote`

Write extracts to temp files as JSON.

### 4 — compile ledger

<!-- GATE — commented out for simplicity
```bash
cnd gate <slug>
```

Does: quote substring check (exact/ws only for high status; fuzzy is soft ->
max SINGLE) -> number/date containment (every figure in `claim` must be in
the quote window) -> negation polarity -> echo near-duplicate collapse (shared
quote/primary/DOI across domains = one unit) -> numeric conflicts ->
depends_on cap -> efficacy primary cap -> status + conf.
No quote -> **UNCHECKED**. Numbers absent from quote -> cannot reach
CORROBORATED. Never hand-promote.
-->

Assemble the claims into a ledger. Note which claims have:
- Multiple independent sources agreeing
- A single source (label as single-source)
- Conflicting numbers or claims (label as contested)
- Only vendor/PR sources (label as interested-party)
- Quotes that couldn't be verified in source text (label as unchecked)

The output is an honest fact document, not a summary.

<!-- SKEPTIC / ADVERSARIAL — commented out for simplicity
### 5 — skeptic / adversarial

If high stakes or only one story cluster: spend reserve (`cnd search --channel adversarial`), `fetch`, extract, `ingest-extract`, **`cnd gate` again**.

```bash
cnd primary-probe <slug>   # DOI/arxiv/NCT hints to chase
cnd fetch <slug> --url '<primary>'
```

High-stakes measurement without opened primary -> leave/capped below
CORROBORATED in clerk notes.
-->

<!-- WRITE — commented out for simplicity
### 6 — merge + write

`cnd write` clusters automatically if `clusters.jsonl` is absent, so an
explicit merge step is not required.

```bash
cnd write <slug> --question "..." --settlement "..."
cnd status <slug>
```

Clerk may edit `~/search/<slug>.md` **only** for: Contested notes, Unknowns,
Evidence quality one-liner -- must not add URLs/numbers absent from
`claims.gated.jsonl`.
-->

### 5 — emit

Present the ledger to the user. Organize by: corroborated findings,
single-source claims, contested claims, unchecked claims. Include source URLs
and note the independence level for each claim.

<!-- STATUS VOCAB — commented out for simplicity
## Status vocab (no SETTLED)

| status | meaning |
|--------|---------|
| CORROBORATED | >=2 independence units, quotes OK, no material clash |
| AUTHORIZED | one entitled originator/primary/official narrow claim |
| CONTESTED | units/numbers disagree |
| SINGLE | one non-vendor unit |
| INTERESTED | vendor/PR only |
| UNCHECKED | quote/fetch fail |
-->

<!-- OUTPUT SHAPE — commented out for simplicity
## Output shape

Published by `cnd write`. Sections: Corroborated, Authorized, Contested,
Single-source, Interested-party, Unchecked, Unknowns, Process audit, Sources.
Process audit stats come from `meta.json` (not vibes).
-->

## Anti-patterns

1. Chat-only condense without verifying quotes against source text
2. Calling marketing a fact after paraphrase
3. Counting different domains as independence when they're all citing the same source
4. Averaging numeric conflicts instead of noting the disagreement
5. Skipping adversarial/disconfirming searches on high-stakes topics
6. Subagents writing directly to `~/search/` directory
7. Stuffing 20 full pages into one prompt
8. Using "settled" (no claim is ever fully settled)
9. Inventing quotes/citations
10. Encyclopedia-only measurements presented as corroborated
11. Quoting a real sentence that states a *different* number than the claim
12. Letting a fuzzy approximate match pass as verified
13. Numbers/dates in the claim that are not in the quote

## Relation

- **dre/deep-research**: long reports
- **cnd**: thin audited ledger

<!-- SMOKE — commented out for simplicity
## Smoke

```bash
cnd init "..." --slug demo && cnd search demo "..." && cnd fetch demo
# extract -> ingest ->
cnd gate demo && cnd write demo
```
-->
