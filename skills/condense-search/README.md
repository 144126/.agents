# condense-search

`cnd` turns web search into a quote-audited fact ledger. One module: `cnd.py`.

## Setup

- CLI: `bin/cnd`
- Needs `FIRECRAWL_API_KEY` in the environment or `~/.agents/secrets/firecrawl.env`

## Flow

1. `cnd init "<subject>" --slug <slug>`
2. `cnd search <slug> "<query>"` — repeat from different angles
3. `cnd fetch <slug>` — parallel scrape, PDF fallback via `pdftotext`
4. Extract per `references/extract_prompt.md` into one JSON per page
5. `cnd ingest-extract <slug> extract.json --source-url <url>`
6. `cnd gate <slug>` — quote and figure gates, echo collapse, status
7. `cnd write <slug> --question "..." --settlement "..."`
8. `cnd selfcheck`

Work lives in `~/search/<slug>/`; the published ledger lands in `~/search/<slug>.md`.

## Guarantees

- Every published claim carries a verbatim quote from a fetched page.
- Every figure and year in the claim text appears near that quote.
- Identical quotes or shared DOI/arxiv/NCT ids across domains count as one origin.
- CORROBORATED requires byte-identical claim wording verified on two or more independent domains.

Not detected: paraphrased syndication, semantic errors, source trustworthiness. The ledger states this on its face.
