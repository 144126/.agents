# condense / `cnd`

Disk-backed claim ledger runner.

```bash
export PATH="$HOME/.agents/skills/condense-search/bin:$PATH"
cnd init "topic" -n 10 --slug my-topic
cnd search my-topic "query" --channel warrant
cnd fetch my-topic
# agent extract → extracts/*.json
cnd ingest-extract my-topic extracts/….json
cnd gate my-topic && cnd merge my-topic && cnd write my-topic
```

- Skill driver: `SKILL.md`
- Epistemology: `references/epistemology.md`
- Extract prompt: `references/extract_prompt.md`
- Firecrawl key (required): `~/.agents/secrets/firecrawl.env` (`FIRECRAWL_API_KEY=...`)

## Search + live fetch (Firecrawl)

`cnd search` returns result urls/titles; `cnd fetch` is the sole path that
pulls page text, via **Firecrawl live scrape** (`max_age=0`, no cache) so the
quote/number gates check against current page text. URLs are deduplicated by
canonicalization (scheme/www/tracking-strip) so the same page isn't fetched
twice or counted as two independent sources. A Firecrawl key is required;
`cnd search`/`cnd fetch` die with a clear message if it's unset.

## Accuracy gates (deterministic, in `cnd gate` / `cnd write`)

- Quote must be verbatim substring; fuzzy (>8% omission) is soft → max SINGLE.
- Every number/date in a claim must appear in the quote window (else `numbers_not_in_quote`).
- Negation polarity must match between quote and claim.
- Near-identical quote / shared primary+number / shared DOI-NCT-arxiv across domains collapse to ONE independence unit.
- Efficacy `measurement` whose primary was not opened is capped at SINGLE.
- `depends_on` children cannot outrank their weakest parent.
- `verify_ledger` blocks `cnd write` if any number/URL in the md is not ⊆ gated claims.
- SETTLED is banned and refused at write.
