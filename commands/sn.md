---
description: Quick search — 3-5 parallel searches, but relentlessly persists until the answer is found.
---

Search for: $ARGUMENTS

You must find a definitive, sourced answer. Do NOT stop until you have one.

## Loop
```
Loop:
  1. Generate 3-5 search phrasings covering different angles
  2. Launch ALL in a single parallel batch
  3. Read promising results, extract what you found (or didn't)
  4. Critic: Did you find the answer with supporting sources?
     → Yes: Exit, synthesize with inline [source URL] citations
     → No:  Refine your approach based on what's missing, loop again
```

- Start fast — 3-5 parallel searches, read 2-3 results, no decomposition tables or confidence scoring
- But if the answer isn't clear, **keep going**. Try completely different phrasings. Use step-back prompting. Approach from contrarian angles. Read more results fully.
- Each round's phrasings must be substantially different from previous rounds — don't repeat yourself
- Cite every factual claim inline [source URL]
