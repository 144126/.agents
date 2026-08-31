---
name: rethink
description: Topic from N angles.
---

# rethink

Uses OpenRouter (OPENROUTER_API_KEY).

User says think about `<topic>` from N angles. If they say fast, add `--fast` (no-op).

```bash
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N
# or, if they named the angles:
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N --angle "..." --angle "..."
```

Do not write the tree or conclusions. Do not invent extra commands.

Non-zero exit or no `~/think/<slug>.conclusions.md` → do not summarize.

When rethink exits 0, summarize that file only. Compress, do not add findings.
