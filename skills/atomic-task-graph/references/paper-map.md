# Paper → implementation map

*Atomic Task Graphs: Structured Planning and Execution for Long-Horizon Agent
Tasks*, arXiv 2607.01942v1. Every mechanism the paper defines, where it lives, the
command that exercises it, and the self-test that proves it.

Run `atg selftest` to execute all 37.

## Definitions (§3)

| paper | here |
|---|---|
| ATG `G = (V, E)`, nodes are atomic tool-use units | `model.py:Graph`, `Node`; a node is atomic exactly when it has `tool:` |
| Definition 3, edges as data dependencies | edges are **inferred** from `$Nj.f` refs — `Graph.edges()`. There is no edge syntax, so a graph cannot claim a dependency it does not have (`t_export_resolution_makes_the_edge`) |
| node interface (inputs, outputs) | `in:` bindings and `out:` fields; `compile.interface_of` |
| refinement depth | dotted id depth — `model.id_depth` (`t_id_helpers`) |

## §4.1 Interface-preserving recursive graph compilation

| paper | file | command | test |
|---|---|---|---|
| recursive decomposition of non-atomic nodes | `compile.refine` | `atg refine` | `t_refine_normalizes_local_ids` |
| termination: recursion stops when every node is one atomic tool-use unit | `Graph.open_nodes` | `atg open`, `atg status` | `t_non_atomic_nodes_are_the_worklist` |
| "the LLM is only allowed to access the historical context directly relevant to the current node" | `compile.context` | `atg context` | `t_end_to_end_figure_3` |
| the surrounding graph remains structurally stable | `exports` blocks + `Graph.resolve_ref` | — | `t_export_resolution_makes_the_edge`, `t_refined_away_ancestor_has_an_interface` |
| interface preservation | `compile.check_interface` | `atg refine` | `t_interface_violations`, `t_interface_warnings` |
| bounded recursion (engineering addition) | `compile.check_budgets` | `--budget` | `t_budget_refusal`, `t_budget_parsing` |

## §4.2 Dependency-aware execution

| paper | file | command | test |
|---|---|---|---|
| thought experiment before execution | `check.py` — `X_TOOL`, `X_MISSING`, `X_DEP`, `X_IFACE`, `X_PATH` | `atg check` | `t_check_clean_and_dirty` |
| agent-found issues counted the same | `check.add_issue`, `check.confirm` | `atg check --add/--confirm` | `t_end_to_end_figure_3` |
| topological order | Kahn's algorithm, `Graph.topo_order` | `atg show` | `t_topology`, `t_cycle_detection_names_the_nodes` |
| executability condition (all inputs recorded) | `schedule.ready` | `atg ready` | `t_scheduler_frontiers`, `t_scheduler_shapes` |
| parallel frontiers | `execute.exec_frontier` | `atg step`, `atg run` | `t_scheduler_shapes`, `t_end_to_end_figure_3` |
| ordering without data (embodied preconditions) | `after:` edges — an extension the paper does not define | — | `t_after_edges_and_heredoc`, `t_after_edge_blocks_until_done` |
| state recording: input, output, status, error | `events.jsonl`, `store.node_states` | `atg node` | `t_run_creation_and_resolution` |
| Table 2 footnote: a parallel frontier is one step | `schedule.levels`, `metrics.collect` | `atg metrics` | `t_metrics_from_canned_events` |

## §4.3 Minimal necessary subgraph repair

| paper | file | command | test |
|---|---|---|---|
| failure localization | `repair.blame` | `atg blame` | `t_execute_repair_reuse_and_freeze` |
| lowest common historical ancestor `a_f` | `repair.prefix_ancestor` and `repair.history_ancestor`, both computed | `atg blame` | `t_lca_prefix_vs_history`, `t_lca_history_beats_prefix` |
| minimal necessary subgraph `M` | `repair.blame` → scope, boundary, stale | `atg blame` | `t_end_to_end_figure_3` |
| "the remaining ATG is frozen to preserve validated states" | `compile.refine(frozen=…)` → `E_FROZEN` | `atg repair` | `t_execute_repair_reuse_and_freeze` |
| reuse of verified intermediate results | `from:` + `repair.reuse_verified` | `atg repair` | `t_end_to_end_figure_3` |
| repair is refinement re-run on `a_f` | `repair.repair` calls `compile.refine` — one code path | `atg repair` | `t_execute_repair_reuse_and_freeze` |
| against global replanning | escalation ladder, repair budgets | `atg blame` | `t_execute_repair_reuse_and_freeze` |

## §5 / Tables and figures

| paper | file | test |
|---|---|---|
| Table 2 — steps, parallel saving | `metrics.collect` | `t_metrics_from_canned_events`, `t_end_to_end_figure_3` |
| Table 3 — hallucinatory action rate, hallucinatory trajectory | `metrics.collect` | `t_metrics_from_canned_events` |
| Fig 6 — risky plans detected, failure precision, repair success, saved environment interactions | `metrics.collect` | `t_end_to_end_figure_3` |
| Figure 3 — the weather example | `templates/example-weather.atg`, `tests/fixtures/weather_g003.atg` | `t_parse_weather_fixture`, `t_end_to_end_figure_3` |

## Where this implementation goes beyond the paper

- **`after:` edges.** Pure data flow cannot express "the fridge must be open before
  the egg can be taken". The paper's embodied benchmarks need it; the format has it.
- **Budgets.** The paper's termination argument is semantic. `max_depth`,
  `max_nodes`, `max_fanout` and the repair budgets bound the engineering failure
  mode where a model recurses or repairs forever.
- **Two LCA derivations.** The paper describes the historical one. Computing the
  prefix as well costs nothing and surfaces provenance bugs as `W_LCA_MISMATCH`.
- **`failure_precision: n/a`.** The paper reports the number from an evaluation
  harness that observed the counterfactual. A normal run does not, so this
  implementation refuses to invent it. See `metrics.md`.
- **Refined-away ancestors get a reconstructed interface.** `a_f` is usually a node
  that no longer exists as a node — outputs come from its surviving `exports` block,
  inputs from the free refs of its subtree (`compile.live_node`).

## Known limits

Inherited from the paper: decomposition quality is bounded by the calling model;
localization degrades under noisy observations and long-range dependencies; on
tasks short enough to finish in one step the bookkeeping costs more than it saves.

Added here: `run:` executes arbitrary shell, so `atg exec` is for graphs the agent
authored and `--dry-run` comes first otherwise; type checking is advisory, because
agent tool spaces are rarely typed and a false blocker is worse than a missed hint.
