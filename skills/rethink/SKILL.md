---
name: rethink
description: Topic from N angles.
---

# rethink

OpenAI-compatible chat. Default `openrouter/z-ai/glm-5.3-flash`. Pass `--model provider/id` and `--reasoning high` to swap.

```bash
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N --model amazon-bedrock-mantle/xai.grok-4.6 --reasoning high
# or named angles:
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N --angle "..." --angle "..."
```

Do not write the tree or conclusions. Do not invent extra commands.

Non-zero exit or no `~/think/<slug>.conclusions.md` → do not summarize.

When rethink exits 0, summarize that file only. Compress, do not add findings.
