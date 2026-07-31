# Metrics

`atg metrics [--json]` folds `events.jsonl` into the numbers the paper reports.
Nothing is stored and incremented — every value is recomputed from the append-only
log, so a read-only command can never inflate one, and any number can be re-derived
later from the run directory alone.

```bash
atg metrics
atg report          # the same table plus the graph, history and timeline, as markdown
```

## Definitions

| metric | definition | paper |
|---|---|---|
| `steps` | distinct dependency levels among completed nodes — a parallel frontier counts once, however wide | Table 2 |
| `serial_steps` | node completions, excluding reuse | — |
| `parallel_saving` | `1 − steps / serial_steps` | §5.3 |
| `frontier_widths` | how many nodes completed at each level | — |
| `executions` | `done` + `fail` events, excluding reuse | — |
| `hallucinatory_action_rate` | executions failing with `X_TOOL` or `X_DEP`, over all executions | Table 3 |
| `hallucinatory_trajectory` | whether the run contains at least one such failure | Table 3 |
| `risky_plans_detected` | fraction of pre-execution checks that produced ≥1 blocking issue | Fig 6 |
| `flagged_nodes` | distinct nodes any check flagged | Fig 6 |
| `failure_precision` | of nodes flagged risky, the fraction that really would have failed | Fig 6 |
| `repairs` | `repair_applied` events | — |
| `repair_success_rate` | repairs after which every previously-failed node reached `done` or was removed | Fig 6 |
| `reused_outputs` | nodes that inherited a verified output via `from:` | Fig 6 |
| `pruned_nodes` | nodes a repair removed entirely | Fig 6 |
| `frozen_not_rerun` | completed nodes a repair froze instead of re-running | Fig 6 |
| `saved_environment_interactions` | `reused + pruned + frozen_not_rerun` | Fig 6 |
| `revisions` / `nodes` / `max_depth` / `open_nodes` | shape of the final graph | — |
| `wall_ms` / `exec_ms` | first to last event; summed node execution time | — |

**Why `steps` is computed, not counted.** Table 2's footnote counts parallel
branches enabled by dependency-aware execution as one step. Deriving it from the
dependency levels of completed nodes makes it reproducible from the log and
immune to how many times you happened to call `atg ready`.

## `failure_precision` prints `n/a` by default

It requires ground truth about a counterfactual: would the flagged node actually
have failed? A normal run never observes that, because the node was repaired and
never ran. So the metric is `n/a` until you supply the answer:

```bash
atg check --confirm N4 true      # it really would have failed
atg check --confirm N4 false     # false alarm
atg run --audit                  # execute flagged nodes unrepaired, record the truth
```

Confirming a node that was never flagged is refused. Emitting a fabricated number
here would be the single easiest way to make this implementation quietly dishonest,
so it does not.

The same discipline applies to the neighbours: `risky_plans_detected` is `n/a` when
no pre-execution check ever ran, and `repair_success_rate` is `n/a` when there were
no repairs. An absent number means the run did not earn one.

## What these numbers do not claim

- They measure **this run**, not the method. A single run's
  `hallucinatory_action_rate` is not the paper's benchmark result.
- `saved_environment_interactions` counts executions **avoided** against the
  baseline of re-running everything downstream of a failure. It is not a wall-clock
  saving, and it says nothing about whether the avoided work would have succeeded.
- `parallel_saving` is structural. It assumes the frontier really did run in
  parallel; with agent-driven execution that is up to you.
- `exec_ms` covers only nodes the CLI executed. Work you did with your own tools has
  no recorded duration unless you supply one.

## Reading the report

`atg report` writes `reports/report.md`: the metrics table, the final graph as
mermaid with per-status colouring, the refinement history (which revision refined
what, and which were repairs), the execution timeline, and the final outputs. It
also drops `metrics.json`, `graph.mmd`, `graph.dot` and `graph.txt` beside it.

The refinement history is usually the most informative part when something went
wrong: it shows where the plan changed shape and how many times a repair had to
touch the same ancestor.
