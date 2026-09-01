---
name: rethink
description: Topic from N angles.
---

# rethink

```bash
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N [--angle "s"]... [--model id]
~/.agents/skills/rethink/bin/rethink.ts <file.r> [--model id]
```

env `RETHINK_MODEL` else `openrouter/z-ai/glm-5.3-flash`. exit 0 writes `~/think/<slug>.conclusions.md`; else do not summarize. on exit 0 summarize that file only.
