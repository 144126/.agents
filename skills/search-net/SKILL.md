---
name: search-net
description: Looping web-search skill. Triggers on 'sn' or 's'. Keeps searching till certain of the answer, then returns a simple concise response. Not for deep research - use 'snx' for that.
---

# SEARCH-NET SKILL

This skill activates when the user message contains 'sn' or 's'. It performs iterative web searches — looping until it's confident the answer is found — then returns a short, direct response without a research breakdown.

## When to Use

Use this skill for:
- Quick factual questions needing verification
- Current information that requires a web lookup
- Simple answers you want confirmed by web sources
- When you want a concise answer, not a research report

## Behavior

When a user message contains 'sn' or 's':
1. Extract the query from the user message
2. Search the web for the answer
3. If the answer is not clear or sources conflict, search again from new angles
4. Keep looping (up to reasonable limit) until confident the answer is correct
5. Return a simple, concise answer — no research breakdown, no source appendix, just the answer

## Example Usage

User: "sn: what was the temperature in Tokyo yesterday?"
Response: "24°C, partly cloudy"

User: "sn: who won the Super Bowl in 2026"
Response: "Kansas City Chiefs"
