---
name: atomic-task-graph
description: Plan and execute a long-horizon task as an Atomic Task Graph — recursive interface-preserving decomposition, a pre-execution thought experiment, parallel dependency-aware execution, and minimal-subgraph repair that freezes validated work instead of replanning. Use for multi-step tasks with real dependencies, real side effects, or a failure that must not throw away everything already verified. Triggers on "atg", "task graph", "decompose this task", "plan then execute", "why did this fail and fix just that part", or any job big enough that a linear plan will drift. Graphs are plain text files you can read, diff and commit. Do not use for a task one tool call finishes.
---

# Atomic Task Graph

An implementation of *Atomic Task Graphs* (arXiv 2607.01942v1) as a deterministic
CLI plus this playbook. The CLI owns everything mechanical — the graph, the
history, the scheduler, the LCA, the frozen set, the metrics. **You** supply the
only things a program cannot: how to decompose a goal, which tool fits, whether a
result is actually right, and what the fix should be.

Nothing here calls a model, opens a socket, or needs an API key. Python 3.9+
stdlib only.

```bash
export PATH="$HOME/.agents/skills/atomic-task-graph/bin:$PATH"
atg version
```

## When to use it

Use it when the task has **parts that depend on each other** and at least one of:
side effects you cannot cheaply repeat (files written, messages sent, money
moved), steps that can run in parallel, or a plan long enough that a failure
halfway through would otherwise mean starting over.

**Do not use it** for anything one or two tool calls finish. The paper's own
limitation applies: on short tasks the bookkeeping costs more than it saves. A
single `grep`, a one-file edit, a question you can answer from memory — just do it.

## The loop

```
init  →  refine* (until nothing is open)  →  check  →  run  →  ┐
                                                               │
              blame → context --repair → repair ← failure ─────┘
                                                               │
                                        metrics / report ← done┘
```

Four mechanisms, each one a command:

| paper | command | what it enforces |
|---|---|---|
| §4.1 interface-preserving compilation | `atg refine` | a subgraph must consume no more than its parent consumed and export everything its parent promised |
| §4.2 thought experiment | `atg check` | five named defect classes are found before anything touches the environment |
| §4.2 dependency-aware execution | `atg ready` / `atg run` | independent nodes run together; a node runs only when every input it names has a recorded value |
| §4.3 minimal subgraph repair | `atg blame` / `atg repair` | a failure is localized to one ancestor; everything else is frozen and cannot be edited |

## 1. Start

```bash
atg tools --init                     # writes tools.atg — EDIT IT (see below)
atg init "<the task, one sentence>" \
    --out answer \
    --input city=beijing \
    --tools tools.atg \
    --acceptance criteria.md
```

`--out` names each field the finished run must produce. `--input k=v` supplies
values reachable as `$task.k`. State-of-the-run lives in `.atg/<run-id>/`;
`$ATG_DIR` moves the root.

**The tool registry is not optional decoration.** `atg check` validates every node
against it, so a registry that lists tools you do not actually have converts a
runtime failure into a passing check — the exact failure mode the paper's
"incorrect tool selection" class exists to catch. Delete what you cannot call.
See `references/tool-registry.md`.

## 2. Decompose

`atg open` lists every node that still has no `tool:` — that is the worklist, and
an empty list is the paper's termination condition. For each one:

```bash
atg context N3                       # read this. it is the whole point.
$EDITOR n3.atg
atg refine N3 --from-file n3.atg
```

`atg context N3` prints **exactly** what N3 may consume, what it must produce, the
interfaces (never the internals) of its immediate neighbours, your tool space, and
the budget left. Refining from anything wider is how models hallucinate steps that
depend on things they were never given. Read it; write the subgraph from it alone.

A refinement fragment uses local ids:

```
node 1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast
  out:  temp_c, precip_mm

node 2
  goal: decide umbrella and clothing from the conditions
  tool: llm_judge
  in:   t = $1.temp_c, p = $1.precip_mm
  out:  advice

exports N3
  advice = $2.advice
```

Three rules, all enforced:

1. **`$1.field` means sibling local node 1.** Refining `N3`, `$1.temp_c` becomes
   `$N3.1.temp_c`. Writing `$2.1.temp_c` means the *child* `N3.2.1`, not the
   sibling `N3.2` — the most common mistake there is.
2. **The `exports` block is mandatory** whenever the parent declares outputs. It
   binds every declared field to a node inside the fragment. Outside nodes keep
   writing `$N3.advice` forever; that is what keeps the rest of the graph
   untouched.
3. **You may only read what the parent read** — its own `in:` bindings, `$task.*`,
   `$env.*`, or any node upstream of the parent. Anything else is `E_IFACE_INPUT`
   and the refinement is refused.

Refusals are the feature. `E_IFACE_*` exits 2, `E_BUDGET` exits 6. Fix the fragment
and resubmit; never work around a refusal by editing the graph by hand.

Details and every error code: `references/compilation.md`, `references/atg-format.md`.

## 3. The thought experiment

Before **anything** touches the environment:

```bash
atg check                            # exit 0 clean, 1 warnings, 2 blocking
```

Layer 1 is deterministic and maps one-to-one onto the paper's five classes:
`X_TOOL` (wrong or misused tool), `X_MISSING` (nobody produces a field somebody
reads), `X_DEP` (cycles, impossible ordering), `X_IFACE` (producer and consumer
disagree), `X_PATH` (unrefined nodes, unreachable nodes, duplicated work).

Layer 2 is **you**, and skipping it defeats the mechanism. Walk the graph in
topological order against the checklist in `references/thought-experiment.md` —
can this tool really produce that output from those inputs; is there an unstated
precondition; does something need to be *put into a state* first. Write findings
back so they count identically to the CLI's own:

```bash
atg check --add X_PATH --node N4 \
  --msg "the fridge must be opened before the egg can be taken" --severity blocking
```

Fix blocking issues by refining or repairing the named node. Never by executing
anyway.

## 4. Execute

```bash
atg ready                            # the frontier, inputs fully resolved
```

Everything `ready` lists can run **now and in parallel** — that is the paper's
executability condition, computed, not guessed. Two ways to run it, mixable in one
graph:

**You run it** (normal for real agent tools):

```bash
atg done N7 --out forecast=@out.json     # @file
atg done N7 --out advice=-               # stdin
atg fail N8 --err "no such object: egg" --class X_TOOL
```

**The CLI runs it** — only for nodes carrying `run:`:

```bash
atg exec --dry-run                   # ALWAYS this first
atg run                              # loop frontiers until done or blocked
```

`run:` is arbitrary shell in your environment. `atg exec` is for graphs **you**
authored. For a graph from anywhere else, `--dry-run` and read every line before
you let it run.

Record failures honestly. A `fail` with the real error is what makes localization
work; a node quietly marked `done` with a wrong value poisons everything
downstream and the metrics too.

## 5. Repair, do not replan

```bash
atg blame                            # → failed nodes, a_f, scope, frozen, reusable
atg context N3 --repair              # the above + failure evidence + reusable values
$EDITOR fix.atg
atg repair N3 --from-file fix.atg
atg run
```

`blame` finds the lowest common historical ancestor `a_f` of the failed set two
ways — id prefix and refinement history — and reports a mismatch rather than
hiding it. Everything outside `a_f`'s subtree is **frozen**: `atg repair` refuses
to add, remove or edit any of it (`E_FROZEN`, exit 5). Frozen means *not editable*,
not *not runnable* — a frozen node that never ran still runs afterwards.

Carry verified work forward instead of redoing it:

```
node 1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast
  out:  temp_c, precip_mm
  from: N3.1
```

`from:` makes the new node inherit the old node's recorded output — but only if the
tool and every resolved input are identical. Otherwise it just runs again. That is
the paper's reuse of verified intermediate results, and it is checked, not trusted.

**Escalate in this order, never in a loop:** repair `a_f` → repair its parent →
replan from the root → abort and report what you learned. Budgets stop you at 3
repairs per node and 10 per run; treat hitting one as information, not an obstacle.

`references/repair.md` has the full scope/freeze/reuse semantics.

## 6. Report

```bash
atg metrics                          # the paper's numbers, folded from the log
atg report                           # reports/report.md + graph renders
atg render --as mermaid --status     # paste into markdown
```

`failure_precision` prints `n/a` unless you supplied ground truth
(`atg check --confirm N4 true|false`, or `atg run --audit`), because a node that was
repaired never ran and nothing observed whether it truly would have failed.
Do not report a number the run did not earn. `references/metrics.md` defines each
one.

## Rules that matter

- **Read `atg context` before writing any subgraph.** Not the whole graph, not your
  memory of it. The narrowing is the mechanism.
- **Never hand-edit a file under `.atg/`.** Revisions are append-only history; the
  metrics and the LCA are derived from them. Every legal change has a command.
- **A refusal is information.** `E_IFACE_INPUT` means your decomposition needs an
  input the parent never had — that is a real modelling error, one level up.
- **One node, one atomic tool call.** If you cannot name the single tool that does
  it, it is not atomic yet; refine again.
- **Check before you act, every time.** The entire point is that defects are cheap
  before execution and expensive after.
- **Prefer `after:` to a fake data dependency** when a step needs the world to be
  in some state rather than a value from another node.
- Exit codes are stable and worth branching on: `0` ok, `1` warnings, `2` blocking,
  `3` usage, `4` not found, `5` frozen violation, `6` budget.
- `--json` works on every command.

## References

| file | what |
|---|---|
| `references/cli-reference.md` | every command, flag, exit code |
| `references/atg-format.md` | the `.atg` grammar, ids, refs, exports, canonical form |
| `references/compilation.md` | refinement rules, all `E_IFACE_*`, budgets, worked example |
| `references/thought-experiment.md` | the five classes and the manual checklist |
| `references/repair.md` | LCA, scope, freeze, reuse, escalation |
| `references/tool-registry.md` | writing `tools.atg` for your actual tool space |
| `references/metrics.md` | every metric, and what it does not claim |
| `references/paper-map.md` | paper section → file → command → test |
| `templates/tools.atg` | generic registry to edit down |
| `templates/example-weather.atg` | the paper's Figure 3 as a finished graph |

`atg selftest` runs 37 test cases covering all of it, including the paper's
Figure 3 end to end. Run it if anything behaves surprisingly.
