---
name: search-net-x
description: Multi-pass deep-research skill. Triggers on 'snx'. Burns 8-20+ searches per query, cites everything, returns a comprehensive research-style breakdown with sources, findings, and analysis. Not for quick lookups - use 'sn' for those.
---

# SEARCH-NET-X SKILL

This skill activates when the user message contains 'snx'. It performs exhaustive multi-pass web research with citation tracking and structured breakdowns.

All search goes through Firecrawl (live, never cached). Use the `fc` runner:

- Search: `~/.agents/bin/fc search "<query>" [num] [text_max]`
- Fetch a page: `~/.agents/bin/fc fetch "<url>" [text_max]`

## When to Use

Use this skill when you need:
- Deep, multi-source research with citations
- Structured analysis with findings and evidence
- Comprehensive coverage of a topic
- Verifiable facts with source tracking

## Behavior

When a user message contains 'snx':
1. Extract the research query from the user message
2. Run 8-20+ `~/.agents/bin/fc search "<query>"` calls across multiple angles
3. Track sources and citations per claim (capture the `url` from each result)
4. To read a source's full text, run `~/.agents/bin/fc fetch "<url>"`
5. Identify contradictions and gaps
6. Return a structured research-style breakdown

## Example Usage

User: "snx: latest AI chip developments 2026"
Will produce: multi-source deep research with citations, findings, contradictions, sources appendix

User: "snx: compare Rust vs Go for web services"
Will produce: comparison with evidence per claim, source-based breakdown
