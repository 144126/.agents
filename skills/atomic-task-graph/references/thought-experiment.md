# The thought experiment — paper §4.2

Simulate the plan before the environment ever sees it. Defects are cheap now and
expensive later — a bad tool call may have written a file, sent a message, or spent
money that no repair can take back.

Two layers. Run layer 1 first so your own effort goes only where code cannot decide.

```bash
atg check                # exit 0 clean, 1 warnings, 2 blocking
atg check --strict       # promote every warning to blocking
```

## Layer 1 — deterministic

Maps one-to-one onto the paper's five named classes.

| class | paper wording | what the CLI actually detects |
|---|---|---|
| `X_TOOL` | incorrect tool selection | tool not in the registry; a required argument unbound; an argument the tool does not accept; a declared `out` field the tool does not produce |
| `X_MISSING` | missing intermediate steps | a ref nobody produces; a declared final output not exported; `$task.k` with no such input; `$env.K` unset (warning) |
| `X_DEP` | invalid dependency assumptions | a cycle (naming the participating nodes); `after:` pointing at a node that is not in the graph, or at itself |
| `X_IFACE` | interface mismatches between connected nodes | a ref resolving to a node that does not declare that output; an export target that does not exist; producer type ≠ consumer type when the registry declares types (warning — types are advisory) |
| `X_PATH` | implausible execution paths | a node still without a tool; a node whose output nothing reads; two nodes with the same tool and identical inputs (a wasted environment interaction); fan-in wider than the tool's arity |

Every issue appends a `check_issue` event tagged with the phase, which is what
makes "risky plans detected" and repair effectiveness computable afterwards. A
check run before anything has executed is tagged `pre_exec`; those are the ones
the metric counts.

## Layer 2 — you

The deterministic layer cannot judge whether a step makes *sense*. Walk the nodes
in topological order — `atg show` prints them in that order — and ask, for each:

1. **Can this tool actually produce this output from these inputs?** Not "is it
   plausible" — would this specific call return that specific field. A `web_fetch`
   does not return structured data. An `llm` call does not return a verified fact.
2. **Is there an unstated precondition?** Does a file need to exist, a directory to
   be current, a session to be authenticated, an object to be held? If the world
   must be in a state nobody establishes, add the step or an `after:` edge.
3. **Would a human reviewer expect a step between these two?** The paper's "missing
   intermediate steps" is usually this, not a dangling reference. Fetch → decide,
   with nothing that *reads* the fetched thing, is a gap.
4. **Does the resolved input actually contain what the consumer assumes?** A field
   named `forecast` might be a JSON blob when the consumer wants a number.
5. **Is this node atomic?** If you cannot name the one tool call it becomes, it
   still needs refining — even if it already has a `tool:`.
6. **Is anything here irreversible?** Deletes, sends, payments, pushes. If the plan
   is wrong, this is where the cost lands. Say so explicitly, on the node.
7. **Does the parallel frontier interfere with itself?** Two nodes in the same
   frontier writing the same file, or both mutating one environment state, are
   independent in the graph and dependent in reality. Add an `after:`.

Write findings back so they count exactly like the CLI's own:

```bash
atg check --add X_PATH --node N4 \
  --msg "the fridge must be opened before the egg can be taken" --severity blocking
atg check --add X_TOOL --node N2 \
  --msg "web_fetch returns prose; N3 expects JSON" --severity blocking
```

Then fix each blocking issue by refining or repairing the node it names. Executing
a graph with a known blocking issue defeats the entire mechanism.

## Confirmation

When a flagged node later runs and you learn whether the flag was right:

```bash
atg check --confirm N4 true      # it really would have failed
atg check --confirm N4 false     # false alarm
```

This is the only honest source of `failure_precision`. Without it the metric prints
`n/a`, because a node that was repaired never ran, and nothing observed the
counterfactual. Confirming a node that was never flagged is refused — that would
manufacture precision out of nothing.

`atg run --audit` does the same automatically: it executes flagged nodes
unrepaired and records the real outcome. Only use it when the flagged nodes have no
side effects you would regret.

## When to re-check

- After every refinement that closes the last open node.
- After every repair, before re-running.
- After any change to `tools.atg`.

`atg check` is read-only apart from the event log. There is no reason to skip it.
