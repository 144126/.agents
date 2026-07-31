import os

from .errors import CycleError
from .model import id_sort_key

RUNNABLE = ("pending", "stale")
OPEN = ("pending", "stale", "failed", "running")


def task_value(meta, field):
    inputs = meta.get("inputs") or {}
    if field in inputs:
        return inputs[field]
    if field in ("text", "task", "goal"):
        return meta.get("task")
    return None


def resolve_value(graph, states, meta, value):
    if not hasattr(value, "target"):
        return (True, value.raw)
    if value.target == "task":
        found = task_value(meta, value.field)
        return (found is not None, found)
    if value.target == "env":
        return (value.field in os.environ, os.environ.get(value.field))
    resolved = graph.resolve_ref(value)
    if resolved is None:
        return (False, None)
    node_id, field = resolved
    state = states.get(node_id)
    if state is None or state.status != "done":
        return (False, None)
    if field not in state.output:
        return (False, None)
    return (True, state.output[field])


def resolve_inputs(graph, states, meta, node_id):
    values = {}
    missing = []
    for binding in graph.nodes[node_id].ins:
        ok, value = resolve_value(graph, states, meta, binding.value)
        if ok:
            values[binding.name] = value
        else:
            missing.append("%s = %s" % (binding.name, binding.value.text()))
    return values, missing


def levels(graph, states):
    pred, _succ = graph.adjacency()
    done = set(i for i, s in states.items() if s.status == "done")
    out = {}
    try:
        order = graph.topo_order()
    except CycleError:
        return {}
    for node_id in order:
        if node_id not in done:
            continue
        parents = [p for p in pred[node_id] if p in done]
        out[node_id] = 0 if not parents else 1 + max(out.get(p, 0) for p in parents)
    return out


def frontier_index(graph, states):
    done_levels = levels(graph, states)
    return 1 + max(done_levels.values()) if done_levels else 0


def blocked_by(graph, states, node_id):
    reasons = []
    after = set(graph.nodes[node_id].after)
    for pred_id in graph.preds(node_id):
        if pred_id in after:
            continue
        state = states.get(pred_id)
        if state is None or state.status != "done":
            reasons.append("%s is %s" % (pred_id, state.label() if state else "unknown"))
    for pred_id in graph.nodes[node_id].after:
        state = states.get(pred_id)
        if state is not None and state.status != "done":
            reasons.append("after %s is %s" % (pred_id, state.label()))
    return reasons


def ready(graph, states, meta):
    out = []
    for node_id in graph.display_order():
        state = states.get(node_id)
        if state is None or state.status not in RUNNABLE:
            continue
        if not graph.nodes[node_id].is_atomic:
            continue
        if blocked_by(graph, states, node_id):
            continue
        values, missing = resolve_inputs(graph, states, meta, node_id)
        if missing:
            continue
        out.append((node_id, values))
    return out


def ready_report(run, graph=None, states=None):
    graph = graph if graph is not None else run.read_revision()
    states = states if states is not None else run.node_states(graph)
    meta = run.meta()
    frontier = frontier_index(graph, states)
    nodes = []
    for node_id, values in ready(graph, states, meta):
        node = graph.nodes[node_id]
        nodes.append({"id": node_id, "tool": node.tool, "goal": node.goal,
                      "in": values, "out": list(node.outs), "run": node.run,
                      "timeout": node.timeout})
    ready_ids = set(n["id"] for n in nodes)
    waiting = []
    for node_id in graph.display_order():
        state = states.get(node_id)
        if state is None or state.status not in OPEN or node_id in ready_ids:
            continue
        reasons = blocked_by(graph, states, node_id)
        if state.status == "failed":
            reasons.append("failed: %s — `atg blame` then `atg repair`" % state.error)
        if state.status == "running":
            reasons.append("still running")
        if not graph.nodes[node_id].is_atomic:
            reasons.append("not atomic: needs `atg refine %s`" % node_id)
        _values, missing = resolve_inputs(graph, states, meta, node_id)
        if missing:
            reasons.append("unresolved inputs: " + ", ".join(missing))
        waiting.append({"id": node_id, "why": reasons})
    return {"frontier": frontier, "nodes": nodes, "waiting": waiting}


def is_blocked(report, states):
    if report["nodes"]:
        return False
    return any(s.status in OPEN for s in states.values())


def status_counts(states):
    counts = {}
    for state in states.values():
        counts[state.status] = counts.get(state.status, 0) + 1
    return counts


def frontier_widths(graph, states):
    widths = {}
    for _node_id, level in sorted(levels(graph, states).items(),
                                  key=lambda kv: id_sort_key(kv[0])):
        widths[level] = widths.get(level, 0) + 1
    return [widths[k] for k in sorted(widths)]
