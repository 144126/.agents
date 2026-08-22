---
name: condense-search
description: >-
  Web search condensed into an audited fact ledger — every claim bound to a
  verbatim quote, enforced by the `cnd` gate. Trigger on "cnd",
  "condense-search", "search and condense", "fact list from the web", "what do
  sources actually say". For one text block or file, use `condense`.
---

# Condense-search

CLI: `~/.agents/skills/condense-search/bin/cnd` (called `cnd` below). Needs `FIRECRAWL_API_KEY` in env or `~/.agents/secrets/firecrawl.env`.

1. `cnd init "<subject>" --slug <slug> && cnd search <slug> "<query>"` — search several angles: proponents, critics, independent.
2. `cnd fetch <slug>` — pulls page text.
3. Extract per `references/extract_prompt.md`: verbatim quote (≤40 words) plus claim text; every number/date in the claim must appear in the quote. Save extract JSON, run `cnd ingest-extract <slug>`.
4. `cnd gate <slug>` — bad quotes and unsupported numbers die here. Never edit gated output by hand.
5. `cnd write <slug> --question "..." --settlement "..."`, then show the user the ledger.

No quote, no claim. No "settled". Domains echoing one originator count once. High stakes with a single story cluster: search disconfirming angles, gate again.
