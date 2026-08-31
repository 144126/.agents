---
name: research
description: Quote-audited dynamic thinking (model decides count) + search.
---

Uses z-ai/glm-5.3-flash via OpenRouter (OPENROUTER_API_KEY). Prints each response usage JSON, then a run total.

```bash
# ask
~/.agents/skills/research/bin/research.ts "<question>"
# resume
~/.agents/skills/research/bin/research.ts "<slug>"
# angled
~/.agents/skills/research/bin/research.ts "<question>" --angle "q1" --angle "q2"
```
