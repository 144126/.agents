# Atomic Task Graph — skill design spec

Implementation spec for `~/.agents/skills/atomic-task-graph/`, a harness-agnostic
agent skill implementing **Atomic Task Graph (ATG)**, Zhang et al., arXiv:2607.01942v1,
*"Atomic Task Graph: A Unified Framework for Agentic Planning and Execution"*.

Date: 2026-07-28. Status: approved, phase 1 in progress.

---

## 1. What the paper specifies, and what it leaves open

The paper is conceptual. It gives formal definitions and prose mechanisms but **no
pseudocode, no prompt templates, no data format, no hyperparameters** beyond the
experimental setup. Everything below marked *(engineering)* is this spec supplying
detail the paper does not fix; everything marked *(paper)* is traceable to a
specific passage.

Paper content this spec must honour:

| § | Mechanism | Requirement |
|---|---|---|
| Def 2 | Tool space `𝒯 = {f_k : ℐ_fk → 𝒪_fk}` | tools are atomic, participate only through their input-output interface |
| Def 3 | Agent | plan is a DAG `G=(V,E)`, node `v_j=(i_j, f_j, o_j)`, edge `e_jk: v_j→v_k` means `o_j` is part of `i_k` |
| Core | Problem | find feasible `G*` where every node is a valid tool invocation, every edge a correct dependency, topological execution yields `y ∈ 𝒴_x` |
| 4.1 | Recursive graph compilation | refine non-atomic nodes until all atomic; at each step the LLM sees **only context directly relevant to the current node** |
| 4.1 | Interface preservation | `G_v` replacing `v` must consume the same external inputs and produce output compatible with `o_v` |
| 4.1 | Termination | stop when every node is a single atomic tool-use unit |
| 4.1 | Refinement history | record the intermediate graph at **every** refinement round → `G_0 … G_T` |
| 4.2 | Thought experiment | pre-execution internal simulation; five named issue classes; record the step at which a failure is exposed, plus error type and diagnostics |
| 4.2 | Execution order | topological; a node is executable when all predecessors finished and inputs resolved; independent nodes run in parallel |
| 4.2 | State recording | per node: input, output, execution status, error messages |
| 4.3 | Failure localization | localize to `v_f` or set `ℱ`; trace back through graph evolution history; find lowest common historical ancestor `a_f` |
| 4.3 | Minimal repair | repair subgraph = failed node + relevant upstream context + affected downstream; **freeze the rest**; reintegrate preserving external interface |
| 5.1 | Training-free | inference time only, no fine-tuning, no supervision, no demonstrations |
| Tab 2 | Step counting | parallel branches count as **one** step |

Explicit non-goals: the ALFWorld / WebShop / ScienceWorld benchmark harness, and
any backbone-model integration. The skill is the control framework; the calling
agent is the backbone.

---

## 2. Architecture

The deterministic half of ATG is a CLI. The semantic half is the calling agent.

```
agent (any LLM)                  atg CLI (deterministic, stdlib-only)
─────────────────                ────────────────────────────────────
decompose a node        ──────►  atg refine N3 --from-file sub.atg
                        ◄──────  interface check, splice, write G003.atg

simulate execution      ──────►  atg check
                        ◄──────  5 issue classes, severity, exit code

                        ◄──────  atg ready → frontier + resolved inputs
run tools               ──────►  atg done N7 --out k=v  /  atg fail N8 --err …
                                 (or atg exec runs `run:` commands itself)

                        ◄──────  atg blame → ℱ, a_f, scope M, frozen F
write the repair        ──────►  atg repair N2 --from-file fix.atg
```

Rationale: the operations the paper depends on for its gains — topological
scheduling, interface preservation, LCA tracing, freeze enforcement, frontier-based
step counting — are exactly the operations an LLM performs unreliably in-context.
Making them code is what turns the paper's claims into properties of the system
rather than hopes about the model. Conversely, decomposition, tool choice and
semantic plausibility are exactly what an LLM is for, so the CLI never guesses at
them and never calls a model.

Consequences: no API keys, no network, no GPU, no `pip install`. Identical
behaviour under Claude Code, opencode, Codex, Cursor, or a bare shell.

### 2.1 Layout

```
~/.agents/skills/atomic-task-graph/
  SKILL.md                  ≤350 lines; the loop, the commands, the hard rules
  README.md                 install/use outside any skill system
  DESIGN.md                 this file
  bin/atg                   bash shim → python3 -m atg.cli
  atg/
    __init__.py             __version__, FORMAT_VERSION
    errors.py               AtgError hierarchy, error codes, exit codes
    model.py                Ref, Binding, Node, Graph, ToolSpec, Registry, RunMeta
    dsl.py                  parse + canonical serialize for .atg
    store.py                run dir, revisions, HEAD, events.jsonl, locking
    tools.py                tool registry parse + lookup + arity/type checks
    compile.py              refine, interface preservation, splice, budgets
    check.py                thought experiment, 5 issue classes
    schedule.py             topo rank, ready frontier, cycle detection
    execute.py              frontier execution, ref substitution, subprocess pool
    repair.py               blame, LCA, minimal scope, freeze, splice, reuse
    metrics.py              event fold → the paper's numbers
    render.py               mermaid | dot | ascii | md
    cli.py                  argparse dispatch, --json, exit codes
    selftest.py             assert-based test runner
  references/
    atg-format.md           full DSL grammar + examples + error codes
    compilation.md          how to decompose; interface rules; worked example
    thought-experiment.md   5 classes + semantic checklist + how to record findings
    repair.md               localization → LCA → scope → splice; escalation ladder
    tool-registry.md        declaring the agent's own tool space
    metrics.md              metric definitions mapped to paper tables
    cli-reference.md        every command, flag, exit code, JSON shape
    paper-map.md            paper section → module → test, for traceability
  templates/
    tools.atg               generic agent tool registry (bash/read/write/web/…)
    example-weather.atg     paper Figure 3, fully worked
  tests/
    fixtures/               .atg graphs, canned events.jsonl, golden outputs
```

Python 3.9+ syntax only (no `match`, no PEP 604 unions in annotations) so the
folder is portable to older boxes. Zero third-party imports anywhere.

`bin/atg`:

```bash
#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 -c 'import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module("atg.cli",run_name="__main__")' "$here" "$@"
```

No `PYTHONPATH` export, no `pip -e`, no `__main__.py` shadowing. Works when the
folder is copied anywhere.

---

## 3. Run store

Graph *structure* is versioned text. Runtime *state* is an append-only event log.
They have different lifecycles, and keeping them apart is what makes revision
diffs readable.

```
.atg/<run-id>/
  run.json        id, task, created, cwd, config, head, status, budgets
  task.md         task statement + acceptance criteria (𝒴_x)
  tools.atg       tool registry snapshot for this run
  HEAD            one line: current revision id, e.g. "G003"
  graphs/
    G000.atg      full snapshots, never diffs — this is G_0 … G_T (paper 4.1)
    G001.atg
  events.jsonl    append-only, the only source of truth for node state
  blobs/          outputs above --blob-threshold (default 8192 bytes)
  reports/        metrics.json, report.md, graph.mmd, graph.dot, graph.txt
```

Run dir root: `./.atg` by default, `$ATG_DIR` overrides. Run id
`YYYYMMDD-HHMMSS-<slug>` where slug is the first 24 chars of the task, lowercased,
non-alnum → `-`. `atg` resolves the run as: `--run <id>` flag → `$ATG_RUN` →
the most recently modified run dir → error `E_NO_RUN`.

Full snapshots rather than diffs: text graphs are ~1–4 KB, a 30-revision run is
under 100 KB, and `atg blame` needs random access to any historical revision.
Diffing would trade a rounding error of disk for real complexity.

### 3.1 Event log

One JSON object per line, appended under an advisory `flock` on `run.json`.

```json
{"seq":41,"t":"2026-07-28T10:04:12.881Z","rev":"G003","node":"N3.2","ev":"done",
 "frontier":7,"in":{"t":"18","p":"0"},"out":{"advice":"take a light jacket"},
 "err":null,"ms":812,"src":"exec"}
```

Fields: `seq` monotonic int, `t` UTC ISO-8601 with ms, `rev` revision in force,
`node` id or null, `ev` event type, plus per-type payload. `src` ∈
`{agent, exec, cli}` distinguishes who produced the transition.

Event types:

| event | payload | emitted by |
|---|---|---|
| `init` | task, tools_hash, budgets | `atg init` |
| `refine` | node, new_rev, added[], depth | `atg refine` |
| `check_start` | rev, phase ∈ {pre_exec, mid_exec} | `atg check` |
| `check_issue` | node, class, msg, severity, phase | `atg check` |
| `check_pass` | rev, issue_count | `atg check` |
| `check_confirm` | node, would_have_failed: bool | `atg check --confirm` |
| `ready` | frontier index, nodes[] | `atg ready` |
| `start` | node, resolved_in | exec/agent |
| `done` | node, out, ms | exec/agent |
| `fail` | node, err, class, ms | exec/agent |
| `blame` | failed[], lca, scope[], frozen[] | `atg blame` |
| `repair_applied` | lca, new_rev, added[], removed[], reused[] | `atg repair` |
| `stale` | nodes[] | `atg repair` |
| `prune` | nodes[], reason | `atg repair` |
| `freeze` | nodes[] | `atg repair` |
| `finish` | status ∈ {done, blocked, aborted}, outputs | `atg run`/`atg finish` |

Node status is **derived** by folding the log against the current revision, never
stored: `pending | ready | running | done | failed | skipped | frozen | stale`.
`state.json` may cache the fold; it is regenerable and delete-safe. Fold rule:
last status-changing event for a node wins, except `stale` which overrides `done`
until the node completes again.

---

## 4. The `.atg` text format

### 4.1 Grammar

```
file        := header task_line? (blank | comment | block)*
header      := '# atg/1' (WS key '=' value)*
               keys: rev, parent, refined, kind, created, note
task_line   := 'task:' TEXT
block       := node_block | exports_block | tool_block
node_block  := 'node' ID EOL (INDENT field EOL)+
exports_blk := 'exports' ID EOL (INDENT FIELD '=' ref EOL)+
tool_block  := 'tool' NAME EOL (INDENT tfield EOL)+          # tools.atg only
field       := 'goal:' TEXT
             | 'tool:' NAME
             | 'in:'   binding (',' binding)*
             | 'out:'  NAME (',' NAME)*
             | 'after:' ID (',' ID)*
             | 'run:'  SHELL
             | 'timeout:' INT
             | 'from:' ID
             | 'note:' TEXT
tfield      := 'desc:' TEXT | 'in:' param (',' param)* | 'out:' param (',' param)*
param       := NAME [':' TYPE] ['!']                          # ! = required
binding     := NAME '=' value
value       := STRING | NUMBER | ref | BARE | heredoc
ref         := '$' (ID | 'task' | 'env') '.' FIELD
ID          := 'N' INT ('.' INT)*
heredoc     := '<<<' EOL raw-lines EOL '>>>'
comment     := '#' TEXT                                       # whole-line, or trailing
```

Indentation is any run of spaces ≥1, consistently; tabs rejected (`E_DSL_TAB`).
Continuation: a field's value continues on the next line if that line is indented
strictly deeper than the field's own indent. Strings use `"…"` with `\"`, `\\`,
`\n` escapes. `BARE` is `[A-Za-z0-9_./:@+-]+`. A trailing `#` starts a comment
unless inside a string or heredoc.

### 4.2 Semantics

- **No `tool:` ⇒ non-atomic.** The node is a goal awaiting refinement. This is the
  termination predicate of paper 4.1, made syntactic.
- **Edges are inferred, never declared.** For every `$Nj.f` appearing in `Nk`'s
  `in:`, emit edge `Nj → Nk` labelled `f`. That is Definition 3 read literally, and
  it makes an unresolved reference an automatic dependency error rather than
  something a validator has to be told to look for. `after: Nj` adds a
  control-only edge (ordering without data) for environment-state preconditions —
  "go to the kitchen" before "open the fridge" — which the paper's embodied
  benchmarks require and pure data-flow cannot express.
- **Hierarchical ids.** Refining `N3` produces `N3.1, N3.2, …`. Depth of an id is
  its refinement depth. The paper's *lowest common historical ancestor* is then the
  longest common dotted prefix — O(total id length), no tree walk. The recorded
  history remains authoritative (see §7.2); the prefix is a cross-check.
- **The root is `N0`,** and refining it is the one special case: it emits top-level
  `N1 … Nk` rather than `N0.1 … N0.k`, so ordinary ids stay short. Every other
  refinement nests. A set of failed nodes with no common prefix therefore has `N0`
  — the root — as its lowest common ancestor, which is the correct answer and needs
  no special-casing in `blame`.
- **`exports` preserves the interface.** `exports N3` maps each declared output
  field of `N3` onto a ref inside `N3`'s subgraph. External nodes keep referring to
  `$N3.advice` forever; resolution walks the export map. Therefore **a refinement's
  textual diff is confined to its own block** — paper 4.1's "the surrounding graph
  remains structurally stable" becomes a property of the file, not a claim.
- **Canonical serialization.** `atg fmt` and every write emit: header, blank,
  `task:`, blank, then node blocks in (topological rank, id) order, 2-space indent,
  one space around `=`, `in:` bindings wrapped at 88 columns with continuation
  indent 8, then `exports` blocks in id order. Parse→serialize→parse is a fixed
  point, tested by fuzz.

### 4.3 Example (paper Figure 3, revision 3)

```
# atg/1 rev=G003 parent=G002 refined=N3
task: check tomorrow's weather in beijing, give travel advice

node N1
  goal: fetch tomorrow's forecast for beijing
  tool: weather_api
  in:   city = "beijing", date = $task.date
  out:  forecast

node N3.1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast
  out:  temp_c, precip_mm, wind_kph

node N3.2
  goal: decide umbrella and clothing from the extracted conditions
  tool: llm_judge
  in:   t = $N3.1.temp_c, p = $N3.1.precip_mm, w = $N3.1.wind_kph
  out:  advice

exports N3
  advice = $N3.2.advice
```

### 4.4 Error codes

Parse: `E_DSL_SYNTAX`, `E_DSL_TAB`, `E_DSL_DUP_NODE`, `E_DSL_DUP_FIELD`,
`E_DSL_BAD_ID`, `E_DSL_BAD_REF`, `E_DSL_UNTERMINATED`, `E_DSL_UNKNOWN_FIELD`.
Every parse error carries `file:line:col`, the offending text, and a fix hint.

---

## 5. §4.1 — Interface-preserving recursive graph compilation

### 5.1 Commands

| command | effect |
|---|---|
| `atg init "<task>" [--tools f] [--acceptance f] [--budget k=v]` | create run dir, write `G000.atg` with the single root node `N0` (goal = task, no tool, `out:` = declared final outputs), emit `init` |
| `atg open` | list nodes lacking `tool:` — the refinement worklist. Empty ⇒ compiled |
| `atg context <ID> [--repair]` | print exactly the context permitted for refining `ID` |
| `atg refine <ID> --from-file f` \| `--from -` | validate, splice, write next revision |
| `atg show [--rev G00x]` | print a revision |
| `atg history` | list `G_0…G_T` with the node each refined |
| `atg fmt [file]` | canonicalize in place |

### 5.2 `atg context` — the anti-hallucination lever

Paper 4.1: *"the LLM is only allowed to access the historical context directly
relevant to the current node"*, and paper 1 attributes the reduced hallucinatory
action rate (Table 3) to exactly this narrowing. Making it a command rather than a
sentence in a prompt is what makes it happen. `atg context N3` prints, and nothing
else:

1. the task statement and acceptance criteria,
2. `N3`'s `goal`, `in:` bindings, `out:` fields,
3. for each **direct** predecessor and successor: id, goal, and interface only —
   never their internals or their own subgraphs,
4. the tool registry,
5. the budget remaining (depth, nodes, fanout).

With `--repair` it additionally prints, for each failed node under `ID`: its
recorded error, its resolved inputs, and the boundary values available for reuse.

### 5.3 `atg refine` algorithm

Input: parent id `v`, a subgraph file `G_v`.

1. **Parse** `G_v`. Node ids may be written bare (`node 1`, `node 2`) or already
   prefixed (`node N3.1`); normalize both to `v.k`.
2. **Interface preservation** — the core check. Let `in(v)` be `v`'s bindings,
   `out(v)` its declared outputs, `anc(v)` the transitive predecessors of `v` in the
   current revision.

   | check | rule | code |
   |---|---|---|
   | inputs not widened | every free ref of `G_v` (ref to a node ∉ `G_v`) must appear in `in(v)`, or target `$task.*`, `$env.*`, or a node in `anc(v)` | `E_IFACE_INPUT` |
   | outputs preserved | the `exports v` block binds **every** field of `out(v)` to a ref resolving inside `G_v` | `E_IFACE_OUTPUT` |
   | no side-edges | the operation adds/removes/edits no node outside `G_v` | `E_IFACE_SCOPE` |
   | no self-reference | `G_v` contains no ref to `$v.*` | `E_IFACE_SELF` |
   | acyclic | `G_v` alone, and the spliced whole graph | `E_CYCLE` |
   | orphans | every node in `G_v` lies on a path from an input-consuming node to an exported node | `W_ORPHAN` (warning) |

   `W_ORPHAN` is deliberately non-fatal: a node may exist purely for a side effect
   (`open the fridge`) with no consumed output, which is legal and common in the
   paper's embodied setting.

   Extra exports beyond `out(v)` are permitted with `W_IFACE_WIDE` — widening what a
   subgraph offers cannot break an existing consumer, whereas widening what it
   *consumes* can, so only the input direction is fatal.
3. **Splice**: remove `v`, insert `G_v`'s nodes, install the export map. External
   refs to `$v.f` are **left untouched** and resolved through the map.
4. **Budgets**: `max_depth` (default 5), `max_nodes` (200), `max_fanout` (8 per
   refinement). Violations raise `E_BUDGET` (exit 6). The paper's termination is
   semantic; these bound the engineering failure mode where a model recurses
   forever. Overridable per run at `init`.
5. **Write** `graphs/G<next>.atg` with `parent=<prev> refined=<v>`, advance `HEAD`,
   append `refine`.

### 5.4 Termination

`atg open` empty ⇒ `atg status` reports `compiled` and `atg check` unblocks. Paper
4.1's "recursion stops when each node corresponds to a single atomic tool-use unit"
holds exactly when no node lacks `tool:`.

---

## 6. §4.2 — Dependency-aware execution

### 6.1 Thought experiment — `atg check`

Two layers. Deterministic first, so the agent's semantic effort is spent only on
what code cannot decide.

**Layer 1 (CLI).** Maps one-to-one onto the paper's five named classes:

| paper wording | code | detects |
|---|---|---|
| incorrect tool selection | `X_TOOL` | tool ∉ registry; required arg unbound; unknown arg supplied; declared `out` field ∉ tool's output schema |
| missing intermediate steps | `X_MISSING` | ref to a field nobody produces; declared final output unreachable; no path from task inputs to an export |
| invalid dependency assumptions | `X_DEP` | cycle; ref to a topologically later node; `after:` naming a node that cannot precede |
| interface mismatches between connected nodes | `X_IFACE` | producer field type ≠ consumer param type (when the registry declares types); incomplete export map; export target missing |
| implausible execution paths | `X_PATH` | non-atomic nodes remaining; unreachable nodes; two nodes with identical tool and identical resolved inputs (wasted interaction); fan-in exceeding tool arity |

Severity: `blocking` (exit 2) or `warning` (exit 1). `--strict` promotes warnings.
Every issue appends a `check_issue` event tagged `phase=pre_exec`, which is what
makes "risky plans detected" and repair-effectiveness computable afterwards.

**Layer 2 (agent).** `references/thought-experiment.md` walks the agent
node-by-node in topological order against a fixed checklist — can this tool
plausibly produce this output from these inputs; is there an unstated precondition;
does the environment need to be in a state nobody established; would a human
reviewer expect a step between these two. Findings are written back:

```
atg check --add X_PATH --node N4 --msg "fridge must be opened before taking the egg" --severity blocking
```

so agent-found and CLI-found issues live in one stream and count identically.

`atg check --confirm N4 true|false` records whether a flagged node actually would
have failed — the only honest source of `failure_precision` (§8).

### 6.2 Scheduling

`schedule.py` computes:

- **topological rank** by Kahn's algorithm over inferred + `after:` edges; a cycle
  yields the participating node set for a precise `X_DEP` message rather than a bare
  "cycle detected".
- **ready frontier** = nodes with status `pending` whose every predecessor is `done`
  and whose every `$` ref resolves to a recorded output value. This is paper 4.2's
  executability condition verbatim.
- **frontier index**, incremented once per completed frontier.

`atg ready` prints each ready node with its **fully resolved** inputs — literal
values substituted, blob refs given as paths — so the agent needs no second lookup
before acting. `--json` gives `{frontier: 7, nodes: [{id, tool, goal, in:{…}, run}]}`.

### 6.3 Execution

Two interchangeable paths, usable in the same run:

**Agent-driven.** The agent uses its own tools, then:

```
atg done N7 --out forecast=@out.json     # @file
atg done N7 --out advice=-               # stdin
atg fail N8 --err "no such object: egg" --class X_TOOL
```

**CLI-driven.** Nodes carrying `run:` are executed by `atg exec`:

- resolve `$` refs into the command string; values above `--blob-threshold`
  (8192 B) are written to `blobs/` and substituted as a path,
- `concurrent.futures.ThreadPoolExecutor`, `--jobs` default `min(8, frontier width)`,
- `subprocess.run(shell=True)`, per-node `timeout:` overriding `--timeout` (default
  120 s), capture stdout/stderr/exit code,
- exit 0 ⇒ `done` with `out` bound to stdout (or to named fields when stdout parses
  as JSON with matching keys); non-zero or timeout ⇒ `fail`.

`--dry-run` prints every resolved command without executing — the documented
default when showing a plan to a human. `run:` is arbitrary shell inherited from the
caller's environment; `SKILL.md` and `README.md` state plainly that `atg exec` is
for graphs the agent itself authored, and that `--dry-run` comes first when the
graph came from anywhere else.

`atg step` = ready → exec → advance one frontier. `atg run` loops `step` until
`done`, `blocked` (frontier empty with pending nodes), or a budget trips.

**Step counting.** A completed frontier increments the step counter by exactly 1
regardless of width — Table 2's footnote, *"parallel branches enabled by
dependency-aware execution are counted as one step"*. `serial_steps` counts node
completions in parallel, giving the honest denominator.

### 6.4 State recording

Per paper 4.2 the log records each node's input, output, execution status and error
message; this spec adds wall-ms and frontier index because both are needed for the
metrics the paper itself reports. `atg node N7` prints the full record.

---

## 7. §4.3 — Minimal necessary subgraph repair

### 7.1 `atg blame [ids…]`

Defaults to every currently-`failed` node. Emits:

```json
{"failed":["N3.2"],"lca":"N3","scope":["N3.1","N3.2"],
 "frozen":["N1","N2","N4"],"boundary_inputs":{"N3.1.src":"$N1.forecast"},
 "reusable_outputs":{"N1.forecast":"blobs/ab12…"},"repairs_used":{"N3":1}}
```

### 7.2 Locating `a_f`

Two independent derivations, both computed:

1. **Prefix**: longest common dotted prefix of `ℱ`. O(total id length).
2. **History**: walk `graphs/G*.atg` backwards to the earliest revision in which
   that ancestor existed as a single unrefined node, following `from:` provenance
   for nodes a previous repair inserted.

The history result is authoritative — it is what paper 4.3 describes and it stays
correct when repair introduces nodes whose ids do not encode their true origin. A
disagreement between the two is reported as `W_LCA_MISMATCH`: cheap, and it catches
provenance bugs the moment they appear.

### 7.3 Minimal necessary subgraph

Given `ℱ` and `a_f`, the scope `M` is:

- `ℱ` itself,
- **upstream context**: ancestors of `ℱ` lying inside `a_f`'s subtree,
- **downstream affected**: transitive successors of `ℱ`, restricted to nodes not yet
  `done`. Successors already `done` are marked `stale` and re-run after repair,
  since they consumed an output now known bad.

Nodes outside `a_f` whose output `ℱ` consumes enter as **read-only boundary**: their
recorded values are available to the repair, and they are never regenerated.

`F = V \ M` is the frozen set. `atg repair` **refuses** any submission that adds,
removes or edits a node in `F` (`E_FROZEN`, exit 5). Paper 4.3's *"the remaining ATG
is frozen to preserve validated states"* is thereby an enforced constraint rather
than an instruction the model may drift from.

### 7.4 `atg repair <a_f> --from-file fix.atg`

Runs the **same code path as `refine`** — the repaired subgraph must still export
every field of `out(a_f)` and consume no more than `in(a_f)`. Repair is refinement
re-run on `a_f` with failure evidence attached, which is what the paper describes,
and sharing the implementation means interface preservation cannot diverge between
the two.

Additionally:

- **Reuse.** A new node carrying `from: <old-id>` whose tool and resolved inputs are
  identical to the old node's inherits its recorded output and starts `done`.
  Reported as `reused[]`. This is paper 4.3's reuse of verified intermediate
  results, made mechanical.
- **Revision** written with `kind=repair refined=<a_f>`; `stale`, `prune`, `freeze`
  and `repair_applied` events appended.
- **Budgets**: `max_repairs_per_node` 3, `max_repairs_per_run` 10.

### 7.5 Escalation ladder

On budget exhaustion the skill directs, in order: repair `a_f` → repair
`parent(a_f)` → replan from the root → abort and emit a report. Documented in
`SKILL.md` and `references/repair.md`. The paper argues against global replanning;
this keeps it as an explicit last resort rather than a silent fallback, and it
closes the obvious failure mode of a model repairing the same node forever.

---

## 8. Metrics

`atg metrics [--json]` folds `events.jsonl`. Definitions track the paper's tables.

| metric | definition | paper |
|---|---|---|
| `steps` | completed frontiers; parallel width counts once | Table 2 |
| `serial_steps` | node completions | — |
| `parallel_saving` | `1 − steps/serial_steps` | §5.3 |
| `hallucinatory_action_rate` | executions failing with `X_TOOL` or an env-reported invalid action, over all executions; plus a trajectory-level variant (run contains ≥1) matching Table 3's wording | Table 3 |
| `risky_plans_detected` | fraction of pre-execution `check` runs yielding ≥1 blocking issue | Fig 6 |
| `failure_precision` | of nodes flagged risky, the fraction that would truly have failed | Fig 6 |
| `repair_success_rate` | repairs after which every previously-failed node reaches `done` | Fig 6 |
| `saved_environment_interactions` | executions avoided = pruned-by-pre-execution-repair + reused-across-repair + frozen-not-re-run | Fig 6 |

Plus: wall time, revision count, max depth, node count, frontier width histogram.

**`failure_precision` reports `n/a` by default.** It needs ground truth about
counterfactual failure, which a normal run does not observe — the flagged node was
repaired, so it never ran. It becomes a number only when `atg run --audit` executes
flagged nodes unrepaired, or the agent supplies `atg check --confirm`. Emitting a
fabricated value here would be the single easiest way to make this implementation
quietly dishonest, so it does not.

`atg report` writes `reports/report.md`: metrics table, final graph rendered,
refinement-history summary, failure/repair timeline.

---

## 9. Renderers

`atg render --as mermaid|dot|ascii|md [--rev G00x] [--status] [--history]`

- **mermaid** `flowchart TD`, label `id\ngoal\n[tool]`, edges labelled with the field
  name, `classDef` per status (done/failed/frozen/stale/ready/pending). Renders
  natively in markdown and in Artifacts.
- **dot** emitted as text. No graphviz on this machine, so nothing is rasterised;
  the output is pipe-ready if the user installs one.
- **ascii** layered by topological rank, one frontier per row, box-drawing
  characters, status glyphs. For terminals.
- **md** node table plus adjacency list, for pasting into a reply.
- **`--history`** renders `G_0 → G_T` as a sequence annotated with the node each
  revision refined — the paper's Figure 3.

---

## 10. Tool registry

`tools.atg`, same parser as graphs:

```
tool weather_api
  desc: forecast for a city and date
  in:   city:str!, date:str!
  out:  forecast:json

tool bash
  desc: run a shell command
  in:   cmd:str!
  out:  stdout:str, stderr:str, code:int
```

`!` marks required. Types are advisory strings; an unknown type always passes, so
the registry degrades rather than blocks. **The registry is optional**: without one,
`X_TOOL` and `X_IFACE` checks drop to warnings and `SKILL.md` prompts the agent to
declare its own tool space. `templates/tools.atg` ships a generic registry covering
what most agents have — bash, read, write, edit, glob, grep, web_search, web_fetch,
subagent, ask_user — so the skill is useful on first contact.

---

## 11. CLI surface

```
atg init "<task>" [--tools f] [--acceptance f] [--budget k=v] [--run id]
atg status | history | show [--rev] | open | context <id> [--repair]
atg refine <id> --from-file f|--from -
atg check [--rev] [--strict] [--add CLASS --node id --msg m [--severity s]]
          [--confirm <id> true|false]
atg ready | step | run [--jobs n] [--audit] [--max-frontiers n]
atg exec [--jobs n] [--timeout s] [--dry-run]
atg done <id> --out k=v[,k=v] | atg fail <id> --err m [--class C]
atg node <id> | blame [ids…] | repair <id> --from-file f
atg metrics | report | render --as X [--rev] [--status] [--history]
atg tools [--check] | fmt [file] | selftest | version
```

`--json` on every command. Exit codes: `0` ok, `1` warnings, `2` blocking issues,
`3` usage error, `4` not found, `5` frozen violation, `6` budget exceeded. Codes are
stable API — agents branch on them.

---

## 12. Testing

`atg selftest` runs `atg/selftest.py`, plain `assert`, no pytest, no fixtures
framework — so verification works on a box with nothing installed.

| area | test |
|---|---|
| DSL | parse→serialize→parse is a fixed point, fuzzed over generated graphs; one negative case per `E_DSL_*` code |
| interface | positive and negative case per `E_IFACE_*`, `W_ORPHAN`, `W_IFACE_WIDE` |
| scheduler | known DAGs → expected frontier sequences: chain, diamond, wide fan-out, `after:`-only edges, cycle |
| LCA | prefix vs history agreement over synthetic histories including repair-inserted nodes |
| repair | golden `{scope, frozen, boundary, reusable}` for a fixture graph; `E_FROZEN` on an out-of-scope edit |
| metrics | canned `events.jsonl` → expected numbers, including `failure_precision: n/a` |
| render | golden mermaid/ascii output |
| end-to-end | paper Figure 3 with stubbed `run:` commands: asserts 3 frontiers, correct exports, one injected failure localized to `N3`, repaired locally, 2 nodes reused, frozen set untouched |

---

## 13. Implementation phases

Each phase ends green under `atg selftest`.

1. **Foundation** — scaffold, `bin/atg`, `errors.py`, `model.py`, `dsl.py`,
   `selftest.py` with DSL round-trip + fixtures.
2. **Store** — `store.py`, `tools.py`, `cli.py` with `init/status/show/history/open/fmt/tools/version`.
3. **Compilation** — `compile.py`: `context`, `refine`, interface preservation, splice, budgets.
4. **Scheduling & execution** — `schedule.py`, `execute.py`: `ready/done/fail/exec/step/run/node`.
5. **Thought experiment** — `check.py`: five classes, `--add`, `--confirm`.
6. **Repair** — `repair.py`: `blame`, LCA, scope, freeze, splice, reuse, budgets.
7. **Metrics & render** — `metrics.py`, `render.py`: `metrics`, `report`, `render`.
8. **Skill surface** — `SKILL.md`, `README.md`, `references/*`, `templates/*`,
   end-to-end test, `paper-map.md` traceability table.

---

## 14. Known limits

Inherited from the paper: decomposition quality is bounded by the calling model;
localization degrades under noisy observations and long-range dependencies; ATG adds
overhead on tasks simple enough to do in one step — `SKILL.md` says plainly not to
use it for those.

Added by this implementation: `run:` executes arbitrary shell; `failure_precision`
is unavailable outside audit mode; type checking is advisory only, since agent tool
spaces are rarely typed; and `after:` edges are an extension the paper does not
define, needed because pure data-flow cannot express environment-state
preconditions in embodied settings.
