---
description: Loop DRPE without prompt — DRPE reads ~/54/research queue until empty
---

## d — DRPE Queue Loop

Call `skill("deep-research-prompt-engineer")` without any user prompt. DRPE's Topic Sourcing section handles reading `~/54/research`, picking a topic, and marking it in progress.

When DRPE completes (report saved, topic line removed), call DRPE again without a prompt. Repeat until DRPE reports the queue is empty.

### Algorithm

```
loop:
  invoke skill("deep-research-prompt-engineer") with no prompt
  if DRPE says "research queue empty" → break
  goto loop
```

### Rules
- Pass NO prompt/topic to DRPE. Let DRPE's Topic Sourcing handle reading the queue.
- Serial only. One research at a time.
- Report status: after each completion, print "Topic done, X remaining" (count remaining lines in ~/54/research that don't have `(in progress)`).
- When DRPE reports queue empty, print "Research queue empty. All topics completed."
