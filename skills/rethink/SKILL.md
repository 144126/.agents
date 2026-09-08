---
name: rethink
description: run the rethink cli to write N angles on one topic into ~/think. use when the user says rethink, or asks for N angles. not for ordinary answers.
---

# rethink

```bash
~/.agents/skills/rethink/bin/rethink.ts "<topic>" N [--angle "s"]...
~/.agents/skills/rethink/bin/rethink.ts <file.r>
```

always `openrouter/meta/muse-spark-1.3-contributor`. exit 0 writes `~/think/<slug>.conclusions.md`; else do not summarize. on exit 0 summarize that file only.
