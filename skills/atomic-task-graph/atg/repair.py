from . import compile as compiler
from .errors import Issue, NotFoundError, UsageError, WARNING
from .model import ROOT_ID, common_ancestor, id_parent, id_sort_key, id_subtree
from .schedule import resolve_inputs
from .store import NodeState


def history_parents(run):
    parents = {}
    origins = {}
    previous = set()
    for rev in run.revisions():
        graph = run.read_revision(rev)
        current = set(graph.nodes)
        refined = graph.refined
        for node_id in current - previous:
            if refined:
                parents.setdefault(node_id, refined)
        for node_id, node in graph.nodes.items():
            if node.origin and node.origin != node_id:
                origins.setdefault(node_id, node.origin)
        previous = current
    return parents, origins


def history_chain(node_id, parents, origins, seen=None):
    seen = seen or set()
    if node_id in seen:
        return [ROOT_ID]
    seen = seen | set([node_id])
    origin = origins.get(node_id)
    if origin and origin != node_id:
        return history_chain(origin, parents, origins, seen) + [node_id]
    parent = parents.get(node_id)
    if parent is None or parent == node_id:
        return [ROOT_ID, node_id] if node_id != ROOT_ID else [ROOT_ID]
    return history_chain(parent, parents, origins, seen) + [node_id]


def history_ancestor(run, failed):
    parents, origins = history_parents(run)
    chains = [history_chain(f, parents, origins) for f in failed]
    if not chains:
        return ROOT_ID
    shared = [ROOT_ID]
    for column in zip(*chains):
        first = column[0]
        if all(c == first for c in column):
            if first != ROOT_ID:
                shared.append(first)
        else:
            break
    deepest = shared[-1]
    if len(failed) == 1 and deepest == failed[0]:
        return parents.get(failed[0]) or id_parent(failed[0]) or ROOT_ID
    return deepest


def prefix_ancestor(failed):
    if len(failed) == 1:
        return id_parent(failed[0]) or ROOT_ID
    return common_ancestor(failed)


def blame(run, ids=None, graph=None, states=None, record=True):
    graph = graph if graph is not None else run.read_revision()
    states = states if states is not None else run.node_states(graph)
    if ids:
        for node_id in ids:
            if node_id not in graph.nodes:
                raise NotFoundError("no node %s in %s" % (node_id, graph.rev),
                                    hint="`atg show` lists the current graph")
        failed = sorted(ids, key=id_sort_key)
    else:
        failed = sorted([i for i in graph.nodes if states[i].status == "failed"],
                        key=id_sort_key)
    if not failed:
        raise UsageError("nothing has failed in %s" % graph.rev,
                         hint="pass node ids explicitly to scope a repair anyway")

    by_prefix = prefix_ancestor(failed)
    by_history = history_ancestor(run, failed)
    lca = by_history
    issues = []
    if by_prefix != by_history:
        issues.append(Issue("W_LCA_MISMATCH",
                            "id prefix says %s, refinement history says %s"
                            % (by_prefix, by_history), severity=WARNING,
                            hint="history wins; a node inserted by an earlier repair "
                                 "probably carries a from: that the ids do not encode"))

    scope = sorted(set([lca] + id_subtree(graph.nodes, lca)) & set(graph.nodes),
                   key=id_sort_key)
    frozen = sorted(set(graph.nodes) - set(scope), key=id_sort_key)
    downstream = set()
    for node_id in failed:
        downstream.update(graph.descendants(node_id))
    stale = sorted([i for i in downstream - set(scope) if states[i].status == "done"],
                   key=id_sort_key)
    boundary = compiler.boundary_values(graph, states, lca)
    reusable = {}
    for node_id in scope:
        state = states.get(node_id)
        if state is not None and state.status == "done":
            for field, value in (state.output or {}).items():
                reusable["%s.%s" % (node_id, field)] = value
    result = {
        "rev": graph.rev, "failed": failed, "lca": lca,
        "lca_by_prefix": by_prefix, "lca_by_history": by_history,
        "scope": scope, "frozen": frozen, "stale": stale,
        "boundary_inputs": boundary, "reusable_outputs": reusable,
        "repairs_used": compiler.repair_counts(run),
        "issues": [i.as_dict() for i in issues],
    }
    if record:
        run.append_event("blame", node=lca, rev=graph.rev, src="cli", failed=failed,
                         lca=lca, scope=scope, frozen=frozen, stale=stale)
    return result


def repair(run, node_id, text, filename="<fragment>", note=None):
    graph = run.read_revision()
    if compiler.live_node(graph, node_id) is None:
        raise NotFoundError("no node %s in %s" % (node_id, graph.rev),
                            hint="`atg blame` names the node to repair")
    states = run.node_states(graph)
    failed = sorted([i for i in graph.nodes if states[i].status == "failed"],
                    key=id_sort_key)
    scope = set(compiler.scope_ids(graph, node_id))
    frozen = sorted(set(graph.nodes) - scope, key=id_sort_key)

    outcome = compiler.refine(run, node_id, text, filename=filename, kind="repair",
                              note=note, allow_atomic=True, frozen=set(frozen),
                              src="agent")
    new_graph = outcome["graph"]
    reused = reuse_verified(run, graph, new_graph, states, outcome["rev"])

    downstream = set()
    for target in failed:
        downstream.update(graph.descendants(target))
    fresh_states = run.node_states(new_graph)
    recreated = set(outcome["added"]) & set(graph.nodes)
    stale = sorted([i for i in (downstream | recreated) & set(new_graph.nodes)
                    if fresh_states[i].status in ("done", "failed", "running")
                    and i not in reused],
                   key=id_sort_key)
    if stale:
        run.append_event("stale", rev=outcome["rev"], src="cli", nodes=stale,
                         reason="consumed an output the repair replaced")
    pruned = [i for i in outcome["removed"] if i not in new_graph.nodes]
    if pruned:
        run.append_event("prune", rev=outcome["rev"], src="cli",
                         nodes=pruned,
                         reason="replaced by the repair of %s" % node_id)
    still_frozen = sorted(set(frozen) & set(new_graph.nodes) - set(stale),
                          key=id_sort_key)
    if still_frozen:
        run.append_event("freeze", rev=outcome["rev"], src="cli", nodes=still_frozen)
    run.append_event("repair_applied", node=node_id, rev=outcome["rev"], src="cli",
                     lca=node_id, added=outcome["added"], removed=outcome["removed"],
                     reused=sorted(reused, key=id_sort_key), stale=stale)
    outcome.update({"reused": sorted(reused, key=id_sort_key), "stale": stale,
                    "frozen": still_frozen, "failed_before": failed})
    return outcome


def reuse_verified(run, old_graph, new_graph, states, rev):
    meta = run.meta()
    live = dict(states)
    reused = []
    for node_id in new_graph.topo_order():
        node = new_graph.nodes[node_id]
        if not node.origin or node.origin not in old_graph.nodes:
            continue
        old = old_graph.nodes[node.origin]
        old_state = states.get(node.origin)
        if old_state is None or old_state.status != "done" or old.tool != node.tool:
            continue
        old_values, old_missing = resolve_inputs(old_graph, states, meta, node.origin)
        new_values, new_missing = resolve_inputs(new_graph, live, meta, node_id)
        if old_missing or new_missing or old_values != new_values:
            continue
        if [f for f in node.outs if f not in old_state.output]:
            continue
        out = dict((f, old_state.output[f]) for f in node.outs)
        run.append_event("done", node=node_id, rev=rev, src="reuse", out=out, ms=0,
                         note="reused the verified result of %s" % node.origin)
        carried = NodeState(node_id)
        carried.status = "done"
        carried.output = out
        carried.inputs = new_values
        live[node_id] = carried
        reused.append(node_id)
    return reused


def blame_lines(result):
    lines = ["failed:   %s" % ", ".join(result["failed"]),
             "lca:      %s  (prefix %s, history %s)" % (result["lca"],
                                                        result["lca_by_prefix"],
                                                        result["lca_by_history"]),
             "scope:    %s" % (", ".join(result["scope"]) or "(none)"),
             "frozen:   %s" % (", ".join(result["frozen"]) or "(none)"),
             "stale:    %s" % (", ".join(result["stale"]) or "(none)")]
    if result["boundary_inputs"]:
        lines.append("boundary (read-only, already verified):")
        for key in sorted(result["boundary_inputs"]):
            lines.append("  %s = %s" % (key,
                                        compiler.short(result["boundary_inputs"][key])))
    if result["reusable_outputs"]:
        lines.append("reusable inside the scope (carry with `from:`):")
        for key in sorted(result["reusable_outputs"]):
            lines.append("  %s = %s" % (key,
                                        compiler.short(result["reusable_outputs"][key])))
    used = result["repairs_used"]
    lines.append("repairs used: %d in this run%s" % (
        used["total"],
        ", ".join([""] + ["%s×%d" % (k, v) for k, v in sorted(used["per_node"].items())])))
    for issue in result["issues"]:
        lines.append("%s %s: %s" % (issue["severity"], issue["class"], issue["msg"]))
    lines.append("next: `atg context %s --repair`, write the fix, "
                 "`atg repair %s --from-file fix.atg`" % (result["lca"], result["lca"]))
    return lines
