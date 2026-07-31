# CLI reference

`atg <command> [flags]`. Global: `--json` (machine-readable output on every
command), `--run ID` (operate on a run other than the most recently touched one).

Exit codes are a stable API — branch on them:

| code | meaning |
|---|---|
| 0 | ok |
| 1 | warnings only |
| 2 | blocking issues (a check failed, a refinement was refused, a node failed) |
| 3 | usage error |
| 4 | run or node not found |
| 5 | frozen violation (`E_FROZEN`) |
| 6 | budget exceeded (`E_BUDGET`) |

Runs live under `$ATG_DIR`, defaulting to `./.atg`. With no `--run` and no
`$ATG_RUN`, commands act on the most recently modified run.

## Starting a run

```
atg init "<task>" [--out FIELD]... [--input K=V]... [--tools FILE]
                  [--acceptance FILE] [--budget K=V]... [--run-id ID]
```

Creates `.atg/<run-id>/` and writes `G000.atg` holding the single root node `N0`
whose `out:` is the declared final outputs (default `answer`). `--input` values are
reachable from any node as `$task.<key>`. `--acceptance` is a file of criteria
echoed back by `atg context`. Budgets: `max_depth` (5), `max_nodes` (200),
`max_fanout` (8), `max_repairs_per_node` (3), `max_repairs_per_run` (10).

```
atg runs                     list runs under the root, newest first
atg status                   phase, node states, frontier, the next command to run
atg version
```

Phases: `compiling` (nodes still lack a tool), `compiled`, `executing`, `blocked`
(something failed), `done`.

## Compiling the graph

```
atg open                     nodes with no tool: — the refinement worklist
atg context ID [--repair]    exactly the context permitted for refining ID
atg refine ID --from-file F | --from -
atg show [--rev G00x]        print a revision
atg history                  G000…G00T with the node each one refined
atg fmt FILE [-w] [--parent ID]
```

`atg context ID` prints the task and acceptance criteria, ID's own goal/in/out,
the *interfaces only* of its direct predecessors and successors, the tool
registry, and the remaining budget. `--repair` adds the recorded failures under
ID, the values reusable from inside its subtree, and the read-only boundary values
its subgraph may consume but must not regenerate.

`atg refine` validates the fragment, splices it in, and writes the next revision.
Failure modes: `E_IFACE_SELF`, `E_IFACE_INPUT`, `E_IFACE_OUTPUT`, `E_IFACE_SCOPE`,
`E_CYCLE` (all exit 2), `E_BUDGET` (6), `E_FROZEN` (5). Warnings `W_ORPHAN` and
`W_IFACE_WIDE` do not block.

`atg fmt --parent N3` canonicalizes a refinement fragment, expanding `node 1` and
`$1.field` into `node N3.1` and `$N3.1.field` so you can see exactly what the
refiner will see. `-w` rewrites in place.

## Checking

```
atg check [--rev G00x] [--strict]
atg check --add CLASS --node ID --msg TEXT [--severity blocking|warning]
atg check --confirm ID true|false
```

Runs the deterministic thought experiment over the current graph. `--strict`
promotes every warning to blocking. Each issue appends a `check_issue` event, which
is what makes "risky plans detected" computable later.

`--add` records an issue *you* found; classes are `X_TOOL`, `X_MISSING`, `X_DEP`,
`X_IFACE`, `X_PATH`. `--confirm` records whether a flagged node really would have
failed — the only honest input to `failure_precision`. Confirming a node that was
never flagged is refused on purpose.

## Executing

```
atg ready                            the frontier, with inputs fully resolved
atg exec [--jobs N] [--timeout S] [--blob-threshold BYTES] [--dry-run]
atg step [--jobs N] [--timeout S]    one frontier
atg run  [--jobs N] [--max-frontiers N] [--audit]
atg done ID --out K=V[,K=V]          value, @file, or - for stdin
atg fail ID --err TEXT [--class CLASS]
atg node ID                          the full record of one node
```

`ready` lists only nodes that are runnable now: atomic, not yet done, every
predecessor done, every `$ref` resolving to a recorded value. Everything it lists
is safe to run in parallel.

`exec` runs the frontier's `run:` commands with `subprocess.run(shell=True)` under
a `ThreadPoolExecutor`, `--jobs` defaulting to `min(8, frontier width)`, per-node
`timeout:` overriding `--timeout` (120 s). Exit 0 binds stdout to the node's single
declared output, or — when stdout parses as a JSON object with matching keys — to
the named fields. Non-zero or timeout records a `fail` with class `X_TOOL`. Values
longer than `--blob-threshold` (8192 B) are spilled to `blobs/` and passed as a
path.

`run --audit` executes flagged nodes unrepaired and records the real outcome as a
confirmation. It exists so `failure_precision` can be a number; it also means a
node you flagged as dangerous will actually run. Do not use it on a graph with
side effects you cannot undo.

`atg node ID` also works for an ancestor that was refined away: it prints the
interface its subgraph must honour, plus the state of every node in that subtree.

## Repairing

```
atg blame [ID...]                    localize failure, find a_f, scope the repair
atg repair ID --from-file F | --from -  [--note TEXT]
```

`blame` defaults to every currently-failed node. It reports `a_f` computed both by
id prefix and by refinement history (history wins; a disagreement is
`W_LCA_MISMATCH`), the repair scope, the frozen set, downstream nodes that go
stale, the read-only boundary values, and what is reusable via `from:`.

`repair` runs the same code path as `refine` — same interface preservation, plus
freezing, reuse, and the repair budgets.

## Reporting

```
atg metrics                          the paper's numbers, folded from events.jsonl
atg report                           writes reports/report.md, metrics.json, graph.*
atg render --as mermaid|dot|ascii|md [--rev G00x] [--status] [--history] [-o FILE]
atg tools [--check] [--init]
atg selftest [-v]
```

`render --status` colours nodes by state (done / failed / running / stale / frozen
/ pending / open). `--history` draws the revision chain `G000 → … → G00T` instead of
the graph. `tools --init` copies the generic registry — into the current run if one
exists, otherwise into `./tools.atg` so you can edit it before `atg init --tools`.

## Run directory layout

```
.atg/<run-id>/
  run.json          task, declared outputs, inputs, budgets, status
  task.md           the task statement and acceptance criteria
  tools.atg         the tool registry for this run
  HEAD              current revision id
  graphs/G000.atg…  every revision, append-only
  events.jsonl      every event, append-only, seq-ordered, flock-protected
  blobs/            spilled large values
  reports/          report.md, metrics.json, graph.mmd/.dot/.txt
```

Node state is never stored — it is folded from `events.jsonl` on every read, so the
log is the single source of truth and nothing can drift out of sync with it.
