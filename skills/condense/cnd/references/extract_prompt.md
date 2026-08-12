# Extractor prompt (one page)

You extract **quote-anchored claims** from ONE page. No filesystem. No merge. No status labels.

## Input you receive

- `source_url`
- `source_class`
- `channel` (`warrant` | `outside` | `adversarial`)
- full page text

## Output

Return **only** JSON (no markdown fence):

```json
{
  "source_url": "https://…",
  "source_class": "peer-reviewed",
  "channel": "warrant",
  "fetch_ok": true,
  "claims": [
    {
      "claim": "atomic self-contained sentence; keep scope/method/units/time",
      "type": "measurement",
      "stance": "asserts",
      "quote": "verbatim ≤40-word substring copied from the page",
      "quote2": null,
      "numbers": [{"value": "94.1", "unit": "%", "stat": "VE", "ci": null}],
      "scope": {"population": "…", "timeframe": "…", "location": null},
      "method": "RCT phase 3",
      "derived_from": [],
      "depends_on": [],
      "cited_primary": "title/DOI/URL if page cites one"
    }
  ]
}
```

`type`: `definition` | `observation` | `measurement` | `mechanism` | `testimony` | `prediction` | `norm` | `opinion`  
`stance`: `asserts` | `denies` | `qualifies`

## Rules

1. Every claim needs a **verbatim** `quote` from the page (≤40 words).
2. Do not invent numbers, dates, papers, or URLs.
3. Keep hedges that change strength/scope.
4. Drop nav, cookies, pure fluff, empty headers.
5. One idea per claim. Empty `claims: []` is valid.
6. Fill `cited_primary` when the page points at a paper/DOI/registry for a load-bearing number.
7. Do not call anything a "fact." Do not assign CORROBORATED/status.

### Span-first number rule (gate will enforce this; follow it to avoid rejects)

8. **Every number and date in `claim` must also appear in the `quote` (or the sentence immediately next to it).** If the claim needs a figure the quote does not contain, either drop that figure from the claim or pick a quote that contains it. The orchestrator's gate rejects claims whose numbers/dates are absent from the quote window ("numbers_not_in_quote").
9. **Negation polarity:** do not write a causal/positive claim ("X reduces Y") from a quote that negates ("no effect on Y", "did not reduce"). Match polarity or mark `stance: "denies"`.

After extract, the orchestrator runs `cnd ingest-extract` then `cnd gate` — bad quotes / unsupported numbers die there.
