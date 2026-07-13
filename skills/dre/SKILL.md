---
name: dre
description: >-
  Deep Research → Markdown Report. Use when the user needs multi-source,
  first-person primary research on a specific question — "I want to understand
  how X works from people who actually did it", "find me operator accounts of
  Y", "research Z from real practitioner stories". Triggers on: "deep research",
  "research report", "primary sources", "first-person accounts",
  "build in public", "operator stories", "founder stories", "case studies from
  real people", "authentic sources", "reading list", "curated sources",
  "research this topic", "dre". The defining feature is the authenticity bar:
  ghostwritten SEO listicles and second-hand summaries are discarded; every
  source must be a first-person account with specific numbers, decisions, and
  mistakes. Output is always a structured markdown report saved to disk.
---

# DRE — Deep Research → Markdown Report

Produce a curated, verified reading list on the user's research question and render it as a polished markdown report. The defining feature is the **authenticity bar**: every source must be first-person (written or narrated by the operator themselves), with specific numbers and decisions. Generic SEO listicles and ghostwritten content marketing get discarded.

---

## Step 1 — Frame the question

From the user's request, extract:

- **The core question** (e.g., "how did companies grow from $2M to $10M ARR?")
- **The underlying decision they're trying to make** (e.g., "what should we prioritize? do we need to do many things at once?"). Ask if unclear — the synthesis section of the report should answer this directly.
- **Any context about the user/company that should bias source selection** (their industry, business model, stage). Use what you know from the session; tailor at least one section of the report to their closest analogs.

Announce the frame to the user for confirmation before proceeding.

---

## Step 2 — Fan out parallel research agents

Launch 4 parallel general-purpose agents in a single message, one per source-type "beat". Adapt beats to the topic; for business/growth research the proven set is:

1. **Founder/operator-written essays and company blogs** — personal blogs, transparent company blogs, open-metrics posts
2. **X/Twitter + LinkedIn build-in-public** — people posting their own revenue numbers, P&Ls, real-time milestones
3. **Podcasts, talks, and interviews with transcripts** — operator narrating their own story (prefer transcript availability)
4. **Communities, newsletters with operator guest posts, and aggregated data** — plus anything directly answering the user's underlying decision question

### Agent prompt template

Each agent prompt MUST include:

- The research question and the authenticity bar **verbatim**: "EXTREMELY personal, first-person accounts from the operators themselves, with specific numbers, specific decisions, what they killed, mistakes, internal debates. NOT generic SEO listicles."
- An instruction to use WebSearch + WebFetch extensively (10+ searches) and to verify by fetching the actual content before including it
- **10–20 named candidate sources/people to investigate** (seed with your own knowledge of the space)
- The required output format per source: title, author + role, URL, scope/range covered, 2–4 takeaways with the specific numbers/tactics, one-line "why it's authentic"
- An instruction to maintain a "investigated and discarded" list with reasons
- An instruction to tier results (Tier 1 verified gems / Tier 2 with caveats) and aim for 8–12 verified sources
- The closing line: "Return structured markdown; your final message is data for the orchestrator, not user-facing prose."
- Practical access tips: X URLs usually fail unauthenticated — try threadreaderapp.com/thread/<POST_ID>.html; dead/broken sites → Wayback Machine; note paywalls explicitly.

---

## Step 3 — Synthesize

Merge the four result sets:

- **Dedupe** (the same canonical source often surfaces on multiple beats — merge takeaways, keep the richest version)
- **Tier** the sources into:
  - **Must-reads** (exact match + strongest authenticity) → thematic sections
  - **Cautionary mirror-images** (first-person failure accounts — always include these if found, they're often the most honest)
  - **Honorable mentions**
- Write a **synthesis section** that directly answers the user's underlying decision question, citing the pattern across sources and the counter-cases
- Note access caveats (paywalls, TLS issues, removed posts) inline with each source

---

## Step 4 — Render the markdown report

Use this exact template, filled in with your content:

```markdown
# [REPORT TITLE]

**Research Report · Verified Primary Sources**

*Prepared for [user] · [company] · [Month Year]*

Every source below was fetched and verified as first-person with real numbers; ghostwritten and SEO content was discarded.

---

## 01 — [Section title]

*[Optional one-line section framing, e.g. "If you only read three things: …"]*

### [Author — "Title / one-line story"] [Tag: Top pick | Closest analog | Primary source]
*[Role, company · scope/range covered · format notes (transcript available, etc.)]*
- [https://primary-url]
- [https://companion-url (optional, with parenthetical note)]

- [Takeaway with the SPECIFIC numbers/tactics — **bold the headline fact**]
- [2–4 takeaways total]

> **Why trust it:** [First-person? Real numbers? Public track record? Named caveats/asterisks go here too.]

---

*Use `.source.caution` equivalent for failure accounts — prefix with ⚠️ or mark clearly.*

**Note:** [Access tips, paywall caveats, where the genre thins out, etc.]

---

## 0N — Synthesis — what the pattern actually says

- **Headline finding.** [Evidence across sources.]
- **Second pattern.** […]
- **The counter-case matters:** [Where the pattern breaks and what that implies.]
- **The failure modes:** [From the cautionary accounts.]

---

*Compiled [Month Year] · [N] parallel research passes ([beat names]) · ~[N] sources verified by fetching primary content; ghostwritten/SEO content discarded.*

```

Create the output directory `~/research/` if it doesn't exist, then write the filled markdown to `~/research/<topic-slug>.md`.

---

## Step 5 — Deliver

In chat, give the report path plus a short summary:

- The 3 must-reads
- The one-paragraph answer to the user's underlying question

Don't repeat the whole report in chat — the markdown file is the deliverable.

---

## Quality bar checklist

- [ ] Every included source was actually fetched/verified by an agent, not assumed from memory
- [ ] Sources are first-person; aggregators only included when they carry verbatim operator quotes/data (and labeled as such)
- [ ] Real numbers appear in the takeaways, not paraphrased vibes
- [ ] Failure/cautionary accounts are represented, not just survivor stories
- [ ] The discarded list exists (proves filtering happened)
- [ ] The synthesis answers the user's actual decision, including counter-cases
