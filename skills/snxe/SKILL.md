---
name: snxe
description: Exa deep-research skill. Triggers on 'snxe'. Uses Exa MCP `web_search_advanced_exa` with maxAgeHours:0 for always-fresh multi-pass research with citations. Not for quick lookups - use 'sn' for those.
---

# SNXe SKILL

This skill activates when the user message contains 'snxe'. It performs exhaustive multi-pass web research using the Exa MCP `web_search_advanced_exa` tool with `maxAgeHours: 0` for always-fresh results, citations, and structured breakdowns.

## When to Use

Use this skill when you need:
- Deep, multi-source research with citations (always fresh, no cache)
- Structured analysis with findings and evidence
- Comprehensive coverage of a topic
- Verifiable facts with source tracking

## Behavior

When a user message contains 'snxe':
1. Extract the research query from the user message
2. Always use the Exa MCP tool `web_search_advanced_exa` with `maxAgeHours: 0` for every search
3. Run 8-20+ searches across multiple angles
4. Track sources and citations per claim
5. Identify contradictions and gaps
6. Return a structured research-style breakdown

## Exa MCP Tool Usage

Use `web_search_advanced_exa` (from the Exa MCP server) for all searches. Always include:
- `maxAgeHours: 0` — ensures always-fresh results, never uses cache
- `type: "auto"` — balanced search quality
- `numResults: 10` or more for depth
- Use `includeDomains`/`excludeDomains` for targeted research
- Use `startPublishedDate`/`endPublishedDate` for temporal filtering

## Example Usage

User: "snxe: latest AI chip developments 2026"
Will produce: multi-source deep research with citations, findings, contradictions, sources appendix (all results always fresh)

User: "snxe: compare Rust vs Go for web services"
Will produce: comparison with evidence per claim, source-based breakdown (all results always fresh)
