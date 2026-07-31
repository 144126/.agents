# atomic-task-graph

A working implementation of *Atomic Task Graphs: Structured Planning and Execution
for Long-Horizon Agent Tasks* ([arXiv 2607.01942v1](https://arxiv.org/html/2607.01942v1))
as an agent skill: a deterministic CLI (`atg`) plus a playbook (`SKILL.md`) that
tells a language model how to drive it.

The split is the point. The CLI owns everything mechanical and checkable — the
graph, the revision history, the scheduler, the lowest common ancestor, the frozen
set, the metrics. The calling agent supplies the four things a program cannot: how
to decompose a goal, which tool fits, whether a result is actually right, and what
the fix should be.

**Python 3.9+ stdlib only.** No dependencies, no API keys, no network. Graphs are
plain text you can read, diff and commit.

## Install

```bash
export PATH="$HOME/.agents/skills/atomic-task-graph/bin:$PATH"
atg version
atg selftest        # 37 test cases, including the paper's Figure 3 end to end
```

## One minute

```bash
atg tools --init                      # then edit tools.atg down to what you have
atg init "check tomorrow's weather in beijing, give travel advice" \
    --out answer --input city=beijing --input date=tomorrow --tools tools.atg

atg open                              # → N0
atg context N0                        # what the decomposition may use
atg refine N0 --from-file plan.atg    # writes G001

atg check                             # the thought experiment: 5 defect classes
atg ready                             # the parallel frontier, inputs resolved
atg run                               # or: atg done N1 --out forecast=@out.json

atg blame                             # on failure: where, and what may change
atg context N3 --repair               # failure evidence + reusable outputs
atg repair N3 --from-file fix.atg     # everything else is frozen and refused

atg metrics && atg report
```

## What it actually enforces

The paper describes four mechanisms. Each is a command, and each is a refusal
rather than an instruction a model can drift away from:

- **Interface-preserving refinement.** A subgraph replacing a node must consume no
  more than that node consumed and export everything it promised. Violations are
  `E_IFACE_*`, exit 2, nothing written. Because outside nodes keep referring to
  `$N3.advice` through an `exports` block, a refinement's diff is confined to its
  own block — the surrounding graph is stable as a property of the file.
- **A thought experiment before execution.** Five defect classes drawn from the
  paper — wrong tool, missing step, bad dependency, interface mismatch, implausible
  path — checked deterministically, plus a checklist for the semantic ones only a
  model can judge. Agent-found issues are recorded in the same stream and counted
  identically.
- **Dependency-aware execution.** Nodes with all inputs recorded run together. A
  parallel frontier counts as one step, per Table 2's footnote.
- **Minimal necessary subgraph repair.** A failure is localized to the lowest
  common historical ancestor of the failed set; only that subtree may be rewritten;
  everything else is frozen and `atg repair` refuses to touch it (`E_FROZEN`, exit
  5). Verified outputs carry forward via `from:` — but only when the tool and every
  resolved input match.

`atg repair` runs the *same code path* as `atg refine`, so interface preservation
cannot diverge between planning and repair.

## Layout

```
SKILL.md                  the playbook the agent reads
bin/atg                   entry point
atg/
  model.py dsl.py         graph model and the .atg text format
  store.py                run directory, append-only event log, state fold
  compile.py              §4.1 refinement, interface checks, context, budgets
  schedule.py execute.py  §4.2 frontiers, execution, state recording
  check.py                §4.2 thought experiment
  repair.py               §4.3 blame, LCA, freeze, reuse
  metrics.py render.py    the paper's numbers; mermaid/dot/ascii/md
  cli.py selftest.py
references/               format, compilation, checking, repair, metrics, CLI, paper map
templates/                generic tool registry, the Figure 3 example
tests/fixtures/
DESIGN.md                 the full specification this was built from
```

Node state is never stored. It is folded from `events.jsonl` on every read, so the
log is the single source of truth and nothing can drift out of sync with it.

## Honesty notes

- `failure_precision` reports `n/a` unless ground truth was supplied
  (`atg check --confirm`, or `atg run --audit`). A repaired node never ran, so
  nothing observed whether it truly would have failed. Inventing that number would
  be the easiest way to make this quietly dishonest.
- Type checking is advisory. Agent tool spaces are rarely typed, and a false
  blocker is worse than a missed hint.
- `run:` executes arbitrary shell in your environment. `atg exec` is for graphs the
  agent itself authored; for anything else, `atg exec --dry-run` first and read
  every line.

## Reading order

`SKILL.md` if you are an agent. `references/paper-map.md` if you want to check the
implementation against the paper. `DESIGN.md` if you want the reasoning behind
every choice.
