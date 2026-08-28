---
name: condense-search
description: Web search condensed into a quote-audited fact ledger. Search far and wide, think deep, step through sources one by one like plan, gate every claim on a verbatim quote.
---

# condense-search

`~/.agents/skills/condense-search/bin/cnd` audits quotes. It does not search or fetch.

## 1 — search far and wide

Break the question into every angle: direct, opposite, adjacent fields, who-benefits, common mistakes, data/numbers, contrarian. Default 5–10 angles standalone; configurable via `--turns N` (tri-research uses 18). Each turn is one `firecrawl search` with a distinct query — turns is count of search calls, not source count.

```bash
firecrawl search "<angle>" --limit 10 --json -o "/tmp/fwd-<slug>.json"
```

Run angles in parallel. Read each file fully. Follow up with `firecrawl scrape "<url>"` only when the snippet is cut short.

Think before you fetch: steelman both sides, look for evidence against your first instinct, prefer a concrete decision over a survey.

## 2 — collect sources

```bash
cnd init "<subject>" --slug <slug>
# fetch kept urls in parallel, skip slow
firecrawl scrape "<url1>" -o /tmp/p1.md &
firecrawl scrape "<url2>" -o /tmp/p2.md &
wait
cnd add-source <slug> --url <url1> --title "<title>" --file /tmp/p1.md
# repeat for each kept url
```

## 3 — step through sources sequentially (plan style, no sub-agents)

```bash
cnd next <slug>              # prints next undone {pid, url, txt}
# read txt fully, think deep about THIS page only, write extracts/<pid>.json
cnd next <slug>              # auto-marks previous if its extract exists, prints next; repeat until 0
# or explicit: cnd next <slug> --done <pid>
```

Schema per source, minimal:

```json
{"source_url":"https://…","claims":[{"claim":"atomic sentence with scope","quote":"verbatim ≤40 words from page","cited_primary":null}]}
```

Rules: quote verbatim, every number/date in claim must be in quote, one number per claim, one idea per claim, invent nothing.

## 4 — gate and publish

```bash
cnd ingest-extract <slug> extracts/*.json
cnd gate <slug>   # quote_found + numbers in quote; echo copies collapse
cnd write <slug> --question "..."  # publishes ~/search/<slug>.md
```

No quote, no claim. Answer first in the ledger, then reasons, then strongest case against if found.
