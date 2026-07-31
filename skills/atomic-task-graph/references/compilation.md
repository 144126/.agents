# Compilation — paper §4.1

Recursive decomposition where every step is required to preserve the interface of
the node it replaces. That requirement is what makes the surrounding graph stay
valid while one part of it is rewritten.

## The loop

```bash
atg open                 # what still has no tool:
atg context N3           # what N3 may consume and must produce
$EDITOR n3.atg
atg refine N3 --from-file n3.atg
```

Repeat until `atg open` is empty. That is the paper's termination condition — the
recursion stops when each node corresponds to a single atomic tool-use unit —
turned into a syntactic property: a node with `tool:` is atomic, a node without one
is not.

## `atg context` — the narrowing

The paper attributes its reduced hallucinatory action rate to the LLM only being
allowed to access the context directly relevant to the current node. `atg context`
is that rule made mechanical. It prints, and nothing else:

1. the task statement and acceptance criteria,
2. `N3`'s goal, `in:` bindings, `out:` fields,
3. for each **direct** predecessor and successor: id, goal, and interface only —
   never their internals, never their subgraphs,
4. the tool registry,
5. the budget remaining.

Write the subgraph from that alone. If you find yourself needing something it did
not print, that is a real signal: your decomposition wants an input the parent
never had, and the fix belongs one level up, not in this fragment.

## Writing a fragment

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

- `node 1` → `N3.1`. Bare ids are expanded against the parent.
- `$1.temp_c` → `$N3.1.temp_c` — **sibling** local node 1.
- `$2.1.temp_c` → `$N3.2.1.temp_c` — the *child* of local node 2. Not the sibling.
- `exports N3` is mandatory when the parent declares outputs.
- Fully-qualified ids (`node N3.1`) are accepted too; both forms normalize to the
  same thing. `atg fmt frag.atg --parent N3` shows you exactly what will be spliced.

## What refine checks

Let `in(v)` be the parent's bindings, `out(v)` its declared outputs, `anc(v)` its
transitive predecessors.

| check | rule | code | blocks |
|---|---|---|---|
| inputs not widened | every free ref of the fragment must appear in `in(v)`, or target `$task.*`, `$env.*`, or a node in `anc(v)` | `E_IFACE_INPUT` | yes |
| outputs preserved | the `exports v` block binds **every** field of `out(v)` to a ref resolving inside the fragment | `E_IFACE_OUTPUT` | yes |
| no side edges | no node outside the fragment is added, removed or edited | `E_IFACE_SCOPE` | yes |
| no self-reference | the fragment contains no ref to `$v.*` | `E_IFACE_SELF` | yes |
| acyclic | the fragment alone, and the spliced whole graph | `E_CYCLE` | yes |
| orphans | every node lies on a path to something exported | `W_ORPHAN` | no |
| extra exports | exports beyond `out(v)` | `W_IFACE_WIDE` | no |

`W_ORPHAN` is deliberately non-fatal: a node may exist purely for a side effect
("open the fridge") with no consumed output, which is legal and common.

Widening what a subgraph *offers* cannot break an existing consumer, so extra
exports are a warning. Widening what it *consumes* can, so that is fatal.

**`E_IFACE_SELF` is the subtle one.** A fragment replacing `N3` cannot read
`$N3.anything` — `N3` no longer exists after the splice, and a subgraph consuming
its own parent's output is circular by construction. Read the parent's *inputs*
instead.

## Splice

`refine` removes `v` and its entire subtree, inserts the fragment's nodes, installs
the export map, and writes `graphs/G<next>.atg` with `parent=<prev> refined=v`.
External refs to `$v.f` are left untouched and resolved through the map — which is
why the diff between two revisions is confined to the refined block.

## Budgets

| budget | default | trips when |
|---|---|---|
| `max_fanout` | 8 | one refinement declares more than 8 nodes |
| `max_depth` | 5 | an id would be deeper than 5 levels |
| `max_nodes` | 200 | the whole graph would exceed 200 nodes |
| `max_repairs_per_node` | 3 | see `repair.md` |
| `max_repairs_per_run` | 10 | see `repair.md` |

Set them at `atg init --budget max_depth=7`. `E_BUDGET` exits 6. The paper's
termination argument is semantic; these bound the engineering failure mode where a
model recurses forever. Hitting one usually means the decomposition is too
fine-grained — coarsen it rather than raising the budget.

## Worked failure

```
$ atg refine N2 --from-file bad.atg
E_IFACE_SELF: bad.atg does not preserve the interface of N2
  blocking E_IFACE_SELF N2.1: N2.1 refers to $N2.answer, the node being replaced
      hint: a subgraph cannot consume its own parent's output
  blocking E_IFACE_OUTPUT N2: no export binds N2.answer
      hint: add:
exports N2
  answer = $<inner-node>.answer
  warning W_ORPHAN N2.1: N2.1 feeds nothing exported by N2
      hint: legal for a pure side effect; otherwise wire its output onward
  hint: `atg context N2` prints exactly what it may consume and must produce
```

Exit 2, nothing written. Fix the fragment and resubmit. Never route around a
refusal by editing a file under `.atg/` — the refusal is the mechanism working.
