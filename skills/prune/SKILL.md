---
name: prune
description: Surgical context compaction for Claude Code. A decision model (Haiku 5.5) reads every transcript entry and marks the ones the session no longer needs; those are replaced by short stubs, then the pruned copy is resumed. Use on "prune", "/prune", "lean the conversation", or instead of /compact.
---

# prune

1. Run `node ~/.agents/skills/prune/prune.ts` (newest session of the cwd = this one). Add `--dry` to preview `-`/`+` per entry, `--model <id>` to change the judge, or pass a session id/path.
2. Tell the user the printed line and: `/exit`, then `claude --resume <new id>`.

How: stubs entries, never deletes, so `parentUuid` chains and `tool_use`/`tool_result` pairs stay valid. Protects the first user message, the last 12 messages, thinking blocks (signed), and anything under 300 chars. Only entries after the last `compact_boundary`. Writes a new session file; the original is untouched (rm it yourself once the pruned one works).

Traps: never edit a live session's jsonl in place (Claude Code rewrites it); `claude -p --json-schema` puts the answer in `.structured_output`; use `--no-session-persistence` for the judge so it leaves no transcript.
