---
name: snxe
description: Firecrawl deep-research skill. Triggers on 'snxe'. Runs 8-20+ live Firecrawl searches (always fresh, never cached) with citations and bounded output. Not for quick lookups - use 'sn' for those.
---

# SNXE SKILL (Firecrawl)

Activates when the user message contains 'snxe'. Performs exhaustive multi-pass web
research through Firecrawl (live, never cached), with citation tracking and bounded
per-result output.

## Firecrawl Runner Usage

Use the `fc` runner (wraps the Firecrawl backend):

- Search: `~/.agents/bin/fc search "<query>" [num] [text_max]`
  - `num` default 8; `text_max` caps each result's length (default 8000) — THIS is
    what keeps SNXE output bounded.
- Fetch a page: `~/.agents/bin/fc fetch "<url>" [text_max]`
  - pulls live page text (Firecrawl default is fresh, no cache).

Example:
```
~/.agents/bin/fc search "latest AI chip developments 2026" 9 6000
~/.agents/bin/fc fetch "https://example.com/article" 15000
```

## Behavior

When a user message contains 'snxe':
1. Extract the research query from the user message
2. Run `~/.agents/bin/fc search "<query>" 9 6000` (fresh, bounded)
3. Run 8-20+ searches across multiple angles
4. Track sources and citations per claim (capture each `url`)
5. To read a source's full text, run `~/.agents/bin/fc fetch "<url>"`
6. Identify contradictions and gaps
7. Return a structured research-style breakdown

Keep each individual search's output bounded via the `text_max` arg — never request
full untruncated pages.

## Example Usage

User: "snxe: latest AI chip developments 2026"
Will produce: multi-source deep research with citations, findings, contradictions,
sources appendix (all results always fresh, each bounded).

User: "snxe: compare Rust vs Go for web services"
Will produce: comparison with evidence per claim, source-based breakdown.
