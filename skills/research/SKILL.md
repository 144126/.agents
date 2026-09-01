---
name: research
description: Quote-audited dynamic thinking (model decides count) + search.
---

OpenAI-compatible chat. Default `openrouter/z-ai/glm-5.3-flash`. Pass `--model provider/id` and `--reasoning high` to swap.

```bash
# ask
~/.agents/skills/research/bin/research.ts "<question>"
~/.agents/skills/research/bin/research.ts "<question>" --model amazon-bedrock-mantle/xai.grok-4.6 --reasoning high
# resume
~/.agents/skills/research/bin/research.ts "<slug>"
# angled
~/.agents/skills/research/bin/research.ts "<question>" --angle "q1" --angle "q2"
```
