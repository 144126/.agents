---
name: compare-models
description: >
  Compare two or more AI models on benchmark scores with overlapping and non-overlapping benchmark tables.
  Trigger whenever a user asks to 'compare', 'benchmark', or 'versus' AI models (e.g. 'compare model X vs Y',
  'how does model A compare to B', 'benchmark scores for model C and D', 'which is better, X or Y').
  Also trigger when user asks to add, create, or write a comparison skill. Do NOT trigger for simple
  model version comparisons without benchmarks.
---

# Compare Models Skill

Compare two or more AI models across their benchmark scores. Produce clean, structured tables showing overlapping benchmarks side-by-side, then non-overlapping benchmarks listed separately per model.

## Workflow

### 1. Identify the models

Extract the model names from the user's query. Resolve aliases/shorthand to full names with provider (e.g. "DS V4 Flash" → "DeepSeek V4 Flash (DeepSeek)"). Note the exact variant/reasoning-effort mode being compared (e.g. "Sol max reasoning", "Flash max effort", "high reasoning"). Always label results with the exact mode tested — benchmarks vary dramatically across reasoning levels.

### 2. Research each model's benchmarks

Search for scores from the most authoritative and comprehensive sources:

**Primary sources** — vendor published:
- HuggingFace model card / GitHub README (look for evaluation tables)
- Official model release blog post (e.g. openai.com/index/..., xAI launch post)

**Secondary sources** — independent aggregators with per-benchmark breakdowns:
- Artificial Analysis (artificialanalysis.ai) — check both the model page AND the comparison page (artificialanalysis.ai/models/comparisons/...)
  - Note: AA individual per-evaluation scores are rendered on interactive chart bubbles, not always extractable as plain text. When scores aren't directly visible in fetched text, search for specific numbers from third-party articles that cite them, or note them as unavailable.
- BenchLM (benchlm.ai) — comprehensive per-model benchmark tracking with coverage counts (e.g. "26 of 296 tracked benchmarks"). Flags verified vs provisional scores.
- OpenRouter (openrouter.ai/compare/...) — direct comparison pages; Design Arena Elo for creative tasks

**Tertiary sources** — third-party analysis:
- News articles that reproduce full benchmark tables (VentureBeat, TechCrunch, Ars Technica)
- Independent blog posts with head-to-head testing

Search strategy:
1. Search for each model individually: `"<Model Name>" benchmark scores`
2. Search for direct comparison: `"<Model A>" vs "<Model B>" benchmark`
3. Check Artificial Analysis comparison page at `artificialanalysis.ai/models/comparisons/<model-a>-vs-<model-b>`
4. Check OpenRouter comparison at `openrouter.ai/compare/<provider>/<model>/<provider>/<model>`
5. Check BenchLM for comprehensive coverage count

Always use `maxAgeHours: 0` for freshness. Fetch full pages, don't rely on snippets.

### 3. Collect per-model data

For each model, collect:
- Full model name, provider, release date
- Architecture (total params, active params if MoE, context length)
- The exact reasoning mode or variant tested (e.g. "max", "high", "non-think", "preview")
- Input/output modalities (text only, multimodal, tool use)
- Pricing (input/output per 1M tokens, cache pricing)
- Speed (tokens/sec) and latency (TTFT)
- ALL benchmark scores with exact names as the source labels them
- For BenchLM: note coverage count (e.g. "26 of 296 tracked")

**Important flagging**:
- When a benchmark score comes from the model vendor's own announcement (self-reported), note it with the source
- When independent verification exists from Artificial Analysis or another third party, prefer or flag those numbers
- When a model claims "SOTA" on a benchmark without publishing the exact score, note that explicitly
- When benchmark names look similar but differ (e.g. SEC-Bench Pro vs SWE-bench Pro), disambiguate

### 4. Identify overlapping benchmarks

Compare benchmark names across models. A benchmark **overlaps** when two or more models have scores for the same named evaluation with comparable methodology.

For the overlapping table:
- List the benchmark name
- Show each model's score with its reasoning mode noted
- Add a **Winner** column
- If scores are within 1-2 points, call it a Tie or note the margin
- If one model claims SOTA without a number and the other has a published score, note that honestly

```markdown
| Benchmark | GPT-5.6 Sol (max) | Grok 4.5 (high) | Winner |
|---|---|---|---|
| AA Intelligence Index | 59 | 54 | GPT-5.6 Sol |
| Terminal-Bench 2.1 | SOTA (no # published) | 83.3% | Grok 4.5 (has #) |
```

### 5. List non-overlapping benchmarks

After the overlapping table, list benchmarks unique to each model. If a model has many (10+), group by category: Knowledge, Reasoning, Coding, Agentic, Long Context, Cybersecurity, Creative.

```markdown
## GPT-5.6 Sol benchmarks (no Grok 4.5 equivalent published)

| Category | Benchmark | Score |
|---|---|---|
| Agentic | BrowseComp | 92.2% |
| Agentic | Agents' Last Exam | 53.6 |

## Grok 4.5 benchmarks (no GPT-5.6 Sol equivalent published)

| Category | Benchmark | Score |
|---|---|---|
| Reasoning | GPQA Diamond | 93.1% |
| Coding | SWE Multilingual | 78.0% |
```

If a model has significantly more published benchmarks than the other (e.g. 26 vs 6), note that coverage gap. Newly released models often have sparse overlap — state this explicitly.

### 6. Summary section

```
## Summary

**Model A wins** on [list] — with margins where notable.

**Model B wins** on [list].

[Caveats: source reliability, pricing context, coverage gaps, recency of models.]
```

### 7. Cite sources

```
Sources: [Source description](URL), [Source description](URL)
```

## Output format

Final output in this order:
1. Overlapping benchmarks table (with Winner column)
2. Non-overlapping benchmarks tables (one per model, grouped by category if 10+)
3. Summary (who wins where, coverage gaps, caveats)
4. Sources

Clean plain-Markdown tables only. No commentary or explanation beyond what's in the tables and summary. Concise and information-dense.
