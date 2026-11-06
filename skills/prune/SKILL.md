---
name: prune
description: Surgical context compaction for Claude Code. A judge model (Haiku 5.5) reads every transcript entry and marks the ones the session no longer needs; those become short stubs in a new session file, which you resume. Use on "prune", "/prune", "lean the conversation", or instead of /compact.
---

# prune

1. Run `node ~/.agents/skills/prune/prune.ts` with Bash `timeout: 600000`. It prunes this session (`$CLAUDE_CODE_SESSION_ID`). `--dry` previews `-`/`+` per entry, `--model <id>` swaps the judge, a session id or path prunes another session.
2. Tell the user the printed lines: `/exit`, then `claude --resume <new id>` (re-add any launch flags). Once it works: `rm` the old `.jsonl` (only the file; its folders are shared by symlink).

How: stubs, never deletes, so `parentUuid` chains and `tool_use`/`tool_result` pairs stay valid. Judges only entries of 1000+ chars outside the newest ~20k tokens; never user prompts, compact summaries, thinking (signed), ToolSearch or Skill results. Tool outputs, tool inputs (Write/Edit bodies), assistant text, `!` and slash command output, and screenshots can go. Writes nothing if it frees under ~15k tokens and under 20% (a resume rebuilds the prompt cache); `--force` overrides. Batches of ~60k tokens run in parallel. Only entries after the last `compact_boundary`. The original stays untouched.

Traps:
- Never edit a live session's jsonl in place. Never pick "newest jsonl in the project": parallel sessions and a changed cwd pick the wrong one.
- Claude Code swaps big tool results for disk previews at load (`content-replacement` entries); prune sizes and rewrites those too.
- Auto mode may deny the write as "Session Transcript Tampering" unless the user asked for prune.
- Judge: `claude -p --json-schema` answers in `.structured_output`; `--no-session-persistence` leaves no transcript; unset `CLAUDECODE`, `CLAUDE_EFFORT` and `CLAUDE_CODE_EFFORT_LEVEL` or it inherits the session's max effort. `--bare` refuses OAuth, so it is not used.
