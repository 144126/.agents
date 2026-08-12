# Epistemology for condense

Read this when extracting or merging claims. The agent never sees the world — only ranked documents. Act accordingly.

## The category error to avoid

A sentence stripped of filler is still a **claim**, not a fact. Facts are claims that earned high status by independent support, quote-anchored extraction, and fit to measurement. If you call every assertive sentence a fact, you launder marketing, error, and rumor into confidence.

**Confident tone is not evidence.** Status words are earned by gates below — never by fluency.

## Speech acts (claim types)

| Type | Meaning | How to write |
|------|---------|--------------|
| definition | What a term is taken to mean | "In [source/context], X means …" |
| observation | Something reported as seen/recorded | Include who/where/when if given |
| measurement | Quantity with method or instrument | Keep units, sample, timeframe, CI if given |
| mechanism | How something is said to work | Separate from observed effect |
| testimony | Someone's account | Attribute the speaker |
| prediction | Forward-looking claim | Keep as prediction, not present fact |
| norm | Should / must / policy value | Never rephrase as is |
| opinion | Evaluation without fixed measure | Keep labeled or drop if pure fluff |

## Evidence classes (source tags)

| Class | Examples | Weight |
|-------|----------|--------|
| originator | Maker's own docs/specs for *their* product, API, model, statute text of *that* law, primary source code README from the project | Highest **for what the originator controls**; not automatic truth about independent world effects |
| primary-data | Datasets, instruments, registries, raw tables, filings, original trial publications | High if transparent |
| peer-reviewed | Journal articles, preprints with methods | High for method+result; still check sample |
| official | Government/statistical agencies, courts, standards bodies | High for what they measure; can lag or frame |
| independent-journalism | Outlets that report methods and cite primaries | Medium–high if they show work |
| expert-secondary | Reviews, textbooks, serious explainers, handbooks, encyclopedias (Grokipedia, Wikipedia, etc.) | Medium; **prefer their citations** for load-bearing numbers — encyclopedia text alone cannot top-rank a measurement |
| user-reported | Forums, reviews, social, interviews, operator blogs with lived detail | Medium for experience; low for global causal magnitude |
| vendor-marketing | Company ads, PR, hype landing pages (not the same as originator *docs*) | Low as world-describing fact; high only for "company claims X" |
| unknown | Thin pages, no author, AI-farm SEO, anonymous "top 10" | Lowest; extract cautiously or skip |

**Originator vs vendor-marketing:** Anthropic docs on Claude = originator for product facts. A growth blog saying "10x your life with Claude" = vendor-marketing / unknown. Same domain can hold both; tag by *page role*, not domain alone.

---

## Independence units (not domain counting)

Counting "independent domains" is too cheap. Two blogs, two news outlets, or one paper + eight derivatives can look plural while being **one claim family**.

### Collapse into one independence unit when sources share any of:

1. Same primary paper, DOI, trial ID, docket, or dataset version + same figure
2. Same press release, wire story, or syndicate
3. Near-identical wording or the same odd/round number cluster with no separate method
4. Same author org, funder line, or corporate family
5. Explicit "according to [X]" where X is already in the pool (derivative, not new unit)

### Fields (set at merge)

- `echo_group_id` — stable id for the collapsed family
- `independence_unit` — canonical representative of that family
- `derived_from` — URLs/IDs of upstream primaries when known

**CORROBORATED requires agreement across independence units**, not bare domains.  
A press-release echo across 12 outlets = **one** unit.

---

## Adaptive dual-channel sampling (not prestige monopole, not false balance)

There is **no neutral retrieval**. Search rankers tilt to prestige, brands, and SEO. Soft-preferring "authorities" doubles that tilt. Unsteered retrieval is usually the same ranker bias with no outsider correction.

**Channels are an instrument, not a sacrament.** Split the budget by **claim class**, not always 50/50.

| Claim class of the user's question | Warrant share | Outside share | Adversarial reserve |
|------------------------------------|---------------|---------------|---------------------|
| Spec / law / API / "what ships" / statute text | ~70% | ~20% | ~10% |
| Rates, efficacy, causation, public controversy | ~40% | ~40% | ~20% |
| Lived failure modes / "what broke" / operator reality | ~30% | ~50% | ~20% |
| Default / mixed | ~45% | ~40% | ~15% |

- **Warrant:** originator docs, primary data, peer methods, official/agency/court/standards, strong secondary, encyclopedias that pass role tests
- **Outside:** operators, critics, failed-replication angles, lived experience, serious dissent, minority methods — including careful blogs
- **Adversarial reserve:** held back until after first merge; spent on disconfirming queries for load-bearing high-status clusters (see Skeptic pass). Always spend the reserve on high-stakes topics even if Warrant looks unanimous.

If one channel runs dry after real searches, say so in Unknowns (`Warrant thin` / `Outside thin`) and reallocate leftovers — do not silently fill everything from prestige only.

**Still deprioritize for both channels:** thin SEO listicles, content-farm "best of", uncited AI mashups. Outside ≠ garbage farm.

### Why split at all

- Institutions lag, get captured, or frame measurements.
- Blogs and forums can be clickbait **or** the only honest failure mode.
- Filling only prestige → fake consensus. Filling only outsiders → rumor ledger.
- Adaptive split prevents **false balance** on clean textual/spec questions while keeping outsiders on contested empirical claims.

### Warrant pool (channel A examples)

1. Originator — product docs, RFCs, statute text, API refs
2. Primary data — BLS, ONS, Eurostat, World Bank, OECD, clinicaltrials.gov, registries, filings, original papers
3. Peer methods — papers / systematic reviews with methods
4. Standards / courts / metrology — ISO, NIST, opinions
5. Encyclopedias that pass role tests (below)
6. Independent journalism / textbooks that show work

### Outside pool (channel B examples)

1. Named operator/postmortem blogs with checkable detail
2. User-reported forums, HN, interviews
3. Explicit criticism, limitations, retractions, COI exposés
4. Minority / rival research lines with names and methods
5. Practitioner newsletters that are first-person, not SEO sludge

### Claim-type → which channel is often *load-bearing* (not exclusive)

| Claim kind | Often load-bearing in | Still keep the other channel for |
|------------|----------------------|----------------------------------|
| Product "what ships" | Warrant (originator) | Outside: UI gotchas, outages |
| Legal text / official status | Warrant (text, court) | Outside: how it is enforced or gamed |
| Rates / stats | Warrant (data, papers) | Outside: measurement critiques |
| Mechanism theory | Warrant (papers) | Outside: failed replications |
| "How I built / what broke" | **Outside** | Warrant: specs that claim otherwise |
| Contested public issue | **Both + adversarial** | Never crown one tribe |

### Encyclopedia selection by role tests (not brand fiat)

Do **not** prefer Grokipedia or Wikipedia by doctrine. For definitional / overview slots, score candidates and pick the winner:

1. Cites checkable primaries (DOI, paper, statute, dataset)
2. Separates claim from editorial gloss
3. Shows dates / versions / last-updated
4. Lower synthetic-slop markers (generic multi-topic mush, no citations, buzzword stack)
5. Fetchable, on-topic, specific body

- Query **both** when an overview helps (`site:grokipedia.com`, Wikipedia, topic handbooks).
- Fetch the **role-test winner**. Note which encyclopedia was used and why in Sources or Process audit.
- If tied, prefer the one with better primary trails.
- **Never** treat either encyclopedia as primary data. Load-bearing numbers must be chased to the cited primary when stakes warrant.
- Encyclopedia pages count toward the **Warrant** share, not Outside.
- Encyclopedia text alone **cannot** place a measurement in CORROBORATED; at best AUTHORIZED is wrong here — cap encyclopedia-only measurements at SINGLE unless primaries are opened.

### Dual channel does **not** mean

- Prestige domain alone ⇒ CORROBORATED
- Outside agreement alone ⇒ "hidden truth" over primary measurements without marking CONTESTED
- Ignoring careful outsider posts because .gov is silent
- Filling all of `n` with one agency family **or** one forum echo
- Equating PageRank with measured true
- Forced 50/50 false balance on a pure spec/law question
- Soft-prefer monopole of authorities

### Within-channel ranking only

Inside a single channel, rank candidates by: on-topic body, independence, specificity, fetch quality, primary-trail quality.  
**Across channels, do not drop Outside claims just because Warrant is quieter or more prestigious.** Merge by independence-unit and conflict rules below.

---

## Quote anchor law (anti-invention)

Extractors **hallucinate**. Paraphrase-only "support" is not enough.

Every claim object **must** carry:

- `quote`: verbatim substring from the fetched page body (≤40 words; prefer the sentence that warrants the claim)
- optional `quote2` if the warrant spans two short spans
- `quote_found`: set by **orchestrator** after substring check (extractor may propose; orchestrator decides)

### Orchestrator reject rules

Reject (or mark UNCHECKED and exclude from CORROBORATED/AUTHORIZED) when:

1. `quote` is missing or empty
2. `quote` is not a literal substring of the stored page text (allow light whitespace normalization only: collapse runs of whitespace, ignore leading/trailing space)
3. The quote does not actually support the claim (support fail — demote or drop). A real sentence that mentions the topic but states a *different* number or opposite polarity cannot corroborate.
4. Numbers/dates in the claim do not appear in the quote or immediate surrounding page context (±2 sentences). The gate computes this deterministically (`numbers_not_in_quote`); an LLM cannot launder a figure the page does not contain.
5. Negation polarity mismatch: a quote with "no effect / did not reduce / fails to" cannot support a causal/positive claim, and vice versa. Deterministic check (`polarity_fail`).

**No quote → no high status.** This is the highest-ROI accuracy gate in the skill.

Fuzzy (non-verbatim, >8% char-omission) quotes are soft: they may reach SINGLE at most, never CORROBORATED/AUTHORIZED.

Store cleaned page text in memory keyed by URL at fetch time so the substring check is real.

---

## Primary chase rule

Secondary sources (news, blogs, encyclopedias, explainers) often launder one trial or press line.

For every **load-bearing** measurement or mechanism cluster:

1. Extract the secondary claim + any cited primary title / DOI / link / trial id
2. Prefer fetching the primary (paper, registry, statute, dataset table)
3. Ledger the **primary** wording when available; keep secondaries as echo/support
4. If primary not opened:
   - status **capped below CORROBORATED** for high-stakes empirical claims (max SINGLE, or CONTESTED if conflict)
   - Unknowns **must** say which primaries were not opened
5. Journalism that shows its primary and matches an opened primary may share the primary's independence unit (derivative), not mint a second unit

---

## Numeric ledger (before prose merge)

Build an in-memory table for every measurement-like claim:

```text
quantity | value | unit | population | timeframe | method | source_url | independence_unit | quote_ok
```

Gates:

| Condition | Action |
|-----------|--------|
| Same quantity, incompatible values across units | Forced **CONTESTED** — never average |
| Relative change with no absolute base rate | Flag on the line; note in Unknowns; do not rewrite as absolute |
| Unitless or population-stripped number | Demote confidence; refuse CORROBORATED until scoped |
| Same odd/round number across SEO farms, no method | Collapse echo group; run adversarial search |
| CI / sample / timeframe present in source | Preserve on the ledger line |

Incompatible numbers are a **truth event**, not a wording problem.

---

## Claim graph (dependence)

Optional but required when clusters clearly chain:

- `depends_on: [claim_ids]`

Rules:

- A child claim **cannot** outrank its weakest load-bearing parent
- If base B is CONTESTED, dependents that assume B max out at CONTESTED or SINGLE
- If base is UNCHECKED/INTERESTED, dependents cannot become CORROBORATED

Example: "Policy P will cut emissions 50%" depends on "Technology T scales by 2030" — if T is contested, P's forecast is not clean.

---

## Status after merge (graded — no "SETTLED")

Ban the label **SETTLED**. It reads like metaphysics. Use:

| Status | Meaning |
|--------|---------|
| **CORROBORATED** | ≥2 **independence units** (non-vendor) agree on substance; load-bearing quotes verified (`quote_found=true`); no material unresolved conflict; for high-stakes measurements, primary opened or status justified as multi-primary-secondary with methods |
| **AUTHORIZED** | One clear originator / primary-data / official source for a *narrow* claim that source is entitled to make (e.g. "we ship feature F"; agency table value for year Y; statute text says Z). Quote verified. Not for world-causal marketing. |
| **CONTESTED** | Independence units disagree on the load-bearing point. Write both sides; do not average. |
| **SINGLE** | One non-vendor independence unit only. Useful; not corroborated. |
| **INTERESTED** | Only vendor-marketing / PR family (not careful originator docs). Quarantine. |
| **UNCHECKED** | Fetch failed, body empty, quote missing/failed, or claim not checkable as stated. |

### Confidence band (per cluster, required on CORROBORATED / AUTHORIZED / CONTESTED)

Assign `high` | `medium` | `low` from **structure**, never tone:

| Band | Typical conditions |
|------|-------------------|
| high | ≥2 independence units, quotes OK, methods clear, primaries opened if measurement, no material conflict |
| medium | Authorized single primary/official with clear method; or 2 units but secondary-heavy / thin method |
| low | Fragile scope, missing base rate, partial quote support, high stakes with thin capture, or lingering soft conflict |

Never promote INTERESTED or frail SINGLE into CORROBORATED by confident phrasing.

### Merge weight

- Blog-only mutual agreement on a *measurement* does not outrank a conflicting primary-data/paper number → CONTESTED or primary-with-note.
- Operator Outside sources may outrank dull secondary summaries on *lived failure modes*.
- Warrant and Outside disagreement → **CONTESTED**, never "authorities win by default."
- Echo collapse happens **before** status assignment.

---

## Orchestrator gates (order is mandatory)

Before any cluster receives CORROBORATED or AUTHORIZED:

1. **Quote substring check** — reject/UNCHECKED failures (exact / whitespace only for high status; fuzzy is soft)
2. **Number/date containment** — every number/date in `claim` must sit in the quote window or the claim is flagged `numbers_not_in_quote` and cannot reach high status
3. **Negation polarity** — quote and claim must agree on polarity (`polarity_fail` otherwise)
4. **Echo-family collapse** — assign independence units; near-identical quote across domains, shared cited_primary+number, or shared DOI/NCT/arxiv collapse to ONE unit
5. **Numeric compatibility matrix** — force CONTESTED on hard clashes
6. **Primary chase + hard cap** — open load-bearing primaries; an efficacy measurement whose primary was not opened is capped at SINGLE even with multiple rewrites (`claim_class` threaded from init)
7. **Dependence demotion** — a child cannot outrank its weakest load-bearing parent (`depends_on` cap)
8. **Skeptic / adversarial reserve** — spend reserve queries; fold results
9. **verify_ledger** — before write, every number/URL in the published md must be ⊆ gated claims; on violation `cnd write` refuses
10. **Status + confidence** — only then
11. **Prose ledger** — word lines from surviving clusters; SETTLED is banned and refused at write

All items except the optional adversarial pass are implemented deterministically in `cnd gate` / `cnd write`. Skipping gates to ship a prettier list is a skill violation.

---

## What to preserve (do not "clean away")

- Scope: animal vs human, lab vs field, country, age group, dose
- Method snippets needed for sense ("RCT n=200", "self-report", "model estimate")
- Time stamps and versions
- Uncertainty markers that change meaning: preliminary, estimated, may, associated with (vs causes)
- Negation and contrast ("no effect on Y", "failed to replicate")
- Confidence intervals, sample sizes, pre-registration notes when present

Deleting hedges that carry **scope or strength** is a truth error. Deleting pure fluff ("It is worth noting that") is fine.

---

## First-principles checks (after merge, before final write)

For each load-bearing CORROBORATED / AUTHORIZED / CONTESTED cluster:

1. What is the actual measurable quantity?
2. What population and timeframe?
3. Is a mechanism asserted without data, or data without mechanism?
4. Effect size without base rate? Relative "% better" without absolute?
5. Who benefits if this claim is believed?
6. What would falsify it, and did any source try?
7. Are agreeing sources true independence units or one press-release echo chamber?
8. Did the quote actually survive substring check?
9. If this is high-stakes, was the adversarial reserve spent?

---

## Adversarial retrieval / Skeptic pass

Run extra searches when any of:

- Only one story cluster for a high-stakes claim
- Numbers look surprising / round / repeatedly unchanged across SEO farms
- Health, legal, financial, safety stakes
- Topic historically contested (nutrition, education, macro, AI evals, politics)
- Budget still holds adversarial reserve after first merge

Useful query shapes: "limitations", "criticism", "failed replication", "retraction", "conflict of interest", "null result", "vs" rival, site:gov / site:edu when appropriate, primary paper title + PDF.

**Skeptic role:** after provisional merge, for each top CORROBORATED/AUTHORIZED cluster, form the strongest disconfirming query, fetch 1–3 counters, extract quote-bound claims, and only then freeze status. Skeptic does not write disk; returns claims to orchestrator memory.

---

## Dedup that does not erase truth

- Same substance, same direction → merge; raise corroboration; keep best-sourced wording; list URLs; count **units** not domains.
- Same topic, opposite direction → CONTESTED block, both wordings, no merge into one line.
- Paraphrase of marketing across ten blogs → one INTERESTED line, not ten "facts."
- Secondary rewrites of one primary → one unit rooted at the primary.

---

## Evidence quality (ledger header)

Required top-level judgment after gates:

| Label | When |
|-------|------|
| **strong** | Multiple independence units, quotes verified, primaries opened for key numbers, adversarial pass run, residual unknowns narrow |
| **mixed** | Some corroborated clusters, but secondary-heavy areas, missing primaries, or material contests remain |
| **weak** | Mostly SINGLE / INTERESTED / UNCHECKED, thin Outside or Warrant, failed fetches, or high-stakes with no primary |

Also state in one line: **Main risk of being wrong:** …

If almost everything is SINGLE/INTERESTED/UNCHECKED, evidence quality is **weak** — say so plainly. Silence dressed as a clean fact list is worse than an explicit gap.

---

## Phenomenological honesty

You are not "finding facts in the room." You are:

1. Hearing ranking systems
2. Reading documents
3. Extracting assertions with verbatim anchors
4. Collapsing echoes into independence units
5. Checking numbers against each other
6. Chasing primaries
7. Inviting disconfirmation
8. Writing a ledger a careful human could audit

If sources thin out, **write unknowns**. If your process was weak, **write the process audit**. The ledger is a sample with error bars — not the world.
