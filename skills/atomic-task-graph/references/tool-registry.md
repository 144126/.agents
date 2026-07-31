# The tool registry

`tools.atg` declares the tool space a graph is allowed to use. It is what turns
"incorrect tool selection" — the paper's first defect class — from a judgement call
into a check.

```bash
atg tools --init      # copy the generic template (before or after `atg init`)
$EDITOR tools.atg     # DELETE what you cannot actually call
atg init "<task>" --tools tools.atg
atg tools --check     # sanity-check the registry itself
```

## Format

Same parser as graphs:

```
tool weather_api
  desc: forecast for a city and date
  in:   city:str!, date:str!
  out:  forecast:json

tool bash
  desc: run a shell command in the working directory
  in:   cmd:str!, cwd:str, timeout:int
  out:  stdout:str, stderr:str, code:int
```

- `!` marks a required parameter. `atg check` raises `X_TOOL` for any node that
  does not bind it.
- Types are advisory strings. An unknown type always passes; a mismatch between a
  producer's output type and a consumer's parameter type is a **warning**, because
  agent tool spaces are rarely typed and a false blocker is worse than a missed
  hint.
- `desc:` is what a planning agent reads to choose between tools. Write it for that
  reader — say what the tool returns, not just what it does.

## Why editing it matters more than writing it

A tool declared here but absent from your harness is worse than one left out
entirely: the check passes and the execution fails. That is precisely the failure
the registry exists to prevent, reintroduced by an unedited template.

So: open `tools.atg` and delete every tool you cannot call right now. Rename the
ones whose names differ in your harness. Add the ones that are yours alone. It
takes a minute and it is the difference between a check that means something and a
check that means nothing.

## Without a registry

The registry is optional. Without one, `X_TOOL` and `X_IFACE` checks drop from
blocking to warning and everything else still works — you lose the tool checks, not
the graph. `atg tools` says so, and `atg check` will not pretend a nonexistent
registry validated anything.

## What `atg check` does with it

| condition | class | severity |
|---|---|---|
| node's `tool:` is not declared | `X_TOOL` | blocking (warning if no registry) |
| a required parameter is unbound | `X_TOOL` | blocking |
| a bound argument the tool does not accept | `X_TOOL` | blocking |
| a declared `out:` field the tool does not produce | `X_TOOL` | blocking |
| more arguments than the tool has parameters | `X_PATH` | warning — usually a missing aggregation step |
| producer output type ≠ consumer parameter type | `X_IFACE` | warning |

`atg tools --check` additionally warns about tools with no `desc:` and tools with
no `out:` fields, since nothing downstream can reference an output that was never
declared.

## The generic template

`templates/tools.atg` covers what most agents have: `bash`, `read`, `write`,
`edit`, `glob`, `grep`, `web_search`, `web_fetch`, `subagent`, `ask_user`, `llm`.
It is a starting point to cut down, not a description of your harness.

Two entries worth understanding:

- **`subagent`** — delegate a self-contained sub-task and get a report. Model it as
  one atomic node; do not try to represent the sub-agent's own steps in this graph.
- **`llm`** — one model call that transforms text. Declare its real output field.
  A node whose `out:` is `answer` while the tool produces `text` is an `X_TOOL`
  finding, and correctly so.

## Per-run copies

`atg init --tools tools.atg` copies the file into the run directory. Editing the
original afterwards does not affect a running graph — edit `.atg/<run>/tools.atg`
and re-run `atg check`. That copy is deliberate: a run's checks should reflect the
tool space that run was planned against.
