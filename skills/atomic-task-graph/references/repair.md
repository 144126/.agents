# Minimal necessary subgraph repair — paper §4.3

When something fails, replanning from the root throws away every verified result
and every environment interaction that produced it. Instead: localize the failure
to the smallest ancestor that contains it, rewrite only that subtree, freeze
everything else, and carry verified outputs forward.

```bash
atg blame                       # where did it break, and what may change
atg context N3 --repair         # what the fix may consume and must produce
$EDITOR fix.atg
atg repair N3 --from-file fix.atg
atg run
```

## `atg blame`

Defaults to every currently-failed node; pass ids to scope a repair manually.

```
failed:   N3.3
lca:      N3  (prefix N3, history N3)
scope:    N3.1, N3.2, N3.3
frozen:   N1, N2, N4
stale:    (none)
boundary (read-only, already verified):
  $N1.forecast = rain 3mm
  $N2.place_id = beijing-1
reusable inside the scope (carry with `from:`):
  N3.1.temp_c = 14
  N3.2.place_name = beijing
repairs used: 0 in this run
next: `atg context N3 --repair`, write the fix, `atg repair N3 --from-file fix.atg`
```

### Locating `a_f`

Two independent derivations, both computed every time:

1. **Prefix** — the longest common dotted prefix of the failed set. For a single
   failed node it is that node's parent, because the node itself already failed and
   the fix has to happen one level up.
2. **History** — walk the revisions backwards to the earliest one in which that
   ancestor existed as a single unrefined node, following `from:` provenance for
   nodes an earlier repair inserted.

History is authoritative: it is what the paper describes, and it stays correct when
a repair introduces nodes whose ids do not encode their true origin. When the two
disagree you get `W_LCA_MISMATCH` rather than a silent choice — cheap, and it
catches provenance bugs the moment they appear.

### The scope, and what is frozen

- **scope** — `a_f` and its entire subtree. This is what the repair replaces.
- **frozen** — everything else. `atg repair` refuses to add, remove or edit any of
  it (`E_FROZEN`, exit 5). This is the paper's "the remaining ATG is frozen to
  preserve validated states", enforced rather than requested.
- **boundary** — nodes outside the scope whose outputs the scope consumes. Their
  recorded values are handed to you read-only; the repair may use them and must
  never regenerate them.
- **stale** — nodes outside the scope that already ran and consumed something the
  repair replaces. They are reset to run again afterwards.

**Frozen means not editable, not un-runnable.** A frozen node that never ran still
executes after the repair — in the example above, `N4` is frozen and pending, and
`atg run` executes it once the repaired `N3` produces `advice`.

## Writing the fix

`atg context N3 --repair` prints everything `atg context N3` does, plus:

- the recorded error, class and resolved inputs of every failed node in the scope,
- every output inside the scope that is reusable,
- the read-only boundary values.

The fragment is an ordinary refinement fragment and is validated identically —
`atg repair` runs the same code path as `atg refine`, so the repaired subgraph must
still export every field of `out(a_f)` and consume no more than `in(a_f)`. Sharing
the implementation is deliberate: interface preservation cannot drift apart between
the two commands.

### Reuse with `from:`

```
node 1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast
  out:  temp_c
  from: N3.1
```

The new node inherits `N3.1`'s recorded output — but only if the tool matches and
every resolved input is identical. Otherwise it simply runs again. Nothing is taken
on trust, so a `from:` that no longer applies costs one re-execution rather than a
wrong answer.

Reuse chains: reused values are visible to later nodes in the same repair, so a
fragment can reuse `N3.1` and then reuse `N3.2`, which reads `$N3.1.temp_c`.

## After the repair

`atg repair` writes a revision tagged `kind=repair`, and appends `stale`, `prune`,
`freeze` and `repair_applied` events. Then:

```bash
atg check                  # the repaired plan is a new plan — check it
atg run
```

## Budgets and escalation

`max_repairs_per_node` (3) and `max_repairs_per_run` (10). When one trips, escalate
in this order — never loop on the same node:

1. repair `a_f`,
2. repair `parent(a_f)` — a wider scope, more context, more freedom,
3. replan from the root (`atg repair N0 --from-file plan.atg`),
4. abort and report: `atg report`, then say plainly what failed and what you
   learned.

The paper argues against global replanning; this keeps it as an explicit last
resort rather than a silent fallback, and it closes the failure mode where a model
repairs the same node forever.

Repeated failure at the same node usually means the error is not where it appears.
A node that cannot succeed no matter how it is rewritten is being given a bad input
by something upstream — escalate rather than rewriting it a third time.
