---
name: browser-speed
description: Use when driving websites with agent-browser; minimize end-to-end browser task latency while retaining reliable verification.
---

# Fast agent-browser workflows

Follow higher-priority browser and user instructions. Reuse a warm, named session and existing authorized browser connection when practical; pin shared-CDP sessions to their own tab. Never take over someone else's tab.

For predictable sequences, batch independent or known sequential commands with `agent-browser batch --bail`; stop and inspect when the next action depends on page state. Use scoped or interactive snapshots and targeted waits for the needed element, URL, or confirmation instead of fixed sleeps or full-page reads. Reuse a prepared page or a verified saved flow for repeated work when appropriate. Parallelize only independent tasks in separate sessions. Verify the requested result, especially writes; do not trade correctness for speed.

When optimizing or comparing performance, measure multiple representative end-to-end runs and, where useful, separate page loading, tool overhead, agent reasoning, and server response. Do not assume a single run proves a speed advantage.
