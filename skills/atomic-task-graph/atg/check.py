import os

from .errors import BLOCKING, Issue, NotFoundError, UsageError, WARNING, worst_exit
from .model import ROOT_ID, id_sort_key

CLASSES = ("X_TOOL", "X_MISSING", "X_DEP", "X_IFACE", "X_PATH")
SEVERITIES = (BLOCKING, WARNING)


def check_tools(graph, registry):
    issues = []
    weak = WARNING if registry.is_empty else BLOCKING
    for node_id in graph.node_ids():
        node = graph.nodes[node_id]
        if node.tool is None:
            continue
        spec = registry.get(node.tool)
        if spec is None:
            issues.append(Issue("X_TOOL", "%s uses tool %r, which the registry does not "
                                          "declare" % (node_id, node.tool), node=node_id,
                                severity=weak,
                                hint="declare it in tools.atg, or fix the name; known: "
                                     + (", ".join(registry.names()) or "(none)")))
            continue
        bound = set(b.name for b in node.ins)
        for name in spec.required_params():
            if name not in bound:
                issues.append(Issue("X_TOOL", "%s does not bind required argument %r of %s"
                                    % (node_id, name, node.tool), node=node_id,
                                    hint="add it to in:"))
        known = set(p.name for p in spec.ins)
        for name in sorted(bound - known):
            issues.append(Issue("X_TOOL", "%s passes %r, which %s does not accept"
                                % (node_id, name, node.tool), node=node_id,
                                hint="accepted: " + (", ".join(sorted(known)) or "(none)")))
        declared = set(spec.output_names())
        if declared:
            for field in node.outs:
                if field not in declared:
                    issues.append(Issue("X_TOOL", "%s declares output %r, which %s does not "
                                        "produce" % (node_id, field, node.tool),
                                        node=node_id,
                                        hint="produced: " + ", ".join(sorted(declared))))
        if len(node.ins) > len(spec.ins) and spec.ins:
            issues.append(Issue("X_PATH", "%s passes %d arguments to %s, which takes %d"
                                % (node_id, len(node.ins), node.tool, len(spec.ins)),
                                node=node_id, severity=WARNING,
                                hint="fan-in wider than the tool's arity usually means a "
                                     "missing aggregation step"))
    return issues


def check_refs(graph, meta):
    issues = []
    inputs = meta.get("inputs") or {}
    for node_id in graph.node_ids():
        node = graph.nodes[node_id]
        for ref in node.refs():
            if ref.target == "task":
                if ref.field not in inputs and ref.field not in ("text", "task", "goal"):
                    issues.append(Issue("X_MISSING", "%s reads %s, which the run does not "
                                        "define" % (node_id, ref.text()), node=node_id,
                                        hint="`atg init --input %s=...` supplies it"
                                             % ref.field))
                continue
            if ref.target == "env":
                if ref.field not in os.environ:
                    issues.append(Issue("X_MISSING", "%s reads %s, which is unset in the "
                                        "environment" % (node_id, ref.text()), node=node_id,
                                        severity=WARNING,
                                        hint="export it before `atg exec`"))
                continue
            resolved = graph.resolve_ref(ref)
            if resolved is None:
                issues.append(Issue("X_MISSING", "%s reads %s, but nothing produces it"
                                    % (node_id, ref.text()), node=node_id,
                                    hint="add the producing step, or point at a node that "
                                         "declares that output"))
                continue
            producer, field = resolved
            if field not in graph.nodes[producer].outs:
                issues.append(Issue("X_IFACE", "%s reads %s, but %s declares outputs %s"
                                    % (node_id, ref.text(), producer,
                                       ", ".join(graph.nodes[producer].outs) or "(none)"),
                                    node=node_id,
                                    hint="add %s to %s's out:" % (field, producer)))
        for target in node.after:
            if target not in graph.nodes:
                issues.append(Issue("X_DEP", "%s waits on %s, which is not in the graph"
                                    % (node_id, target), node=node_id,
                                    hint="`atg show` lists the node ids"))
            elif target == node_id:
                issues.append(Issue("X_DEP", "%s waits on itself" % node_id, node=node_id))
    return issues


def check_types(graph, registry):
    issues = []
    if registry.is_empty:
        return issues
    for node_id in graph.node_ids():
        node = graph.nodes[node_id]
        spec = registry.get(node.tool) if node.tool else None
        if spec is None:
            continue
        for binding in node.ins:
            param = spec.param(binding.name)
            if param is None or not param.type or not hasattr(binding.value, "target"):
                continue
            resolved = graph.resolve_ref(binding.value)
            if resolved is None:
                continue
            producer = graph.nodes[resolved[0]]
            producer_spec = registry.get(producer.tool) if producer.tool else None
            if producer_spec is None:
                continue
            out_param = None
            for candidate in producer_spec.outs:
                if candidate.name == resolved[1]:
                    out_param = candidate
            if out_param is None or not out_param.type:
                continue
            if out_param.type != param.type:
                issues.append(Issue("X_IFACE", "%s.%s is %s but %s.%s expects %s"
                                    % (resolved[0], resolved[1], out_param.type,
                                       node_id, binding.name, param.type), node=node_id,
                                    severity=WARNING,
                                    hint="types are advisory; convert it or fix a "
                                         "declaration"))
    return issues


def check_structure(graph, meta):
    issues = []
    try:
        graph.topo_order()
    except Exception as err:
        nodes = getattr(err, "nodes", [])
        issues.append(Issue("X_DEP", "the graph is cyclic among %s" % ", ".join(nodes),
                            node=nodes[0] if nodes else None,
                            hint="break the loop by removing one $ref or after:"))
        return issues
    for node_id in graph.open_nodes():
        issues.append(Issue("X_PATH", "%s has no tool: it is still a goal, not an action"
                            % node_id, node=node_id,
                            hint="`atg refine %s` decomposes it" % node_id))

    exports = graph.exports.get(ROOT_ID)
    declared = meta.get("outputs") or []
    if declared and len(graph.nodes) > 1:
        if exports is None:
            issues.append(Issue("X_MISSING", "nothing exports the final outputs %s"
                                % ", ".join(declared),
                                hint="the refinement of %s must carry an `exports %s` block"
                                     % (ROOT_ID, ROOT_ID)))
        else:
            for field in declared:
                ref = exports.mapping.get(field)
                if ref is None:
                    issues.append(Issue("X_MISSING", "final output %r is not exported"
                                        % field,
                                        hint="add %s = $<node>.%s to exports %s"
                                             % (field, field, ROOT_ID)))
                elif graph.resolve_ref(ref) is None:
                    issues.append(Issue("X_IFACE", "exports %s.%s points at %s, which does "
                                        "not exist" % (ROOT_ID, field, ref.text()),
                                        hint="`atg show` lists the node ids"))

    terminal = terminal_nodes(graph)
    for node_id in graph.node_ids():
        if node_id in terminal:
            continue
        if not graph.succs(node_id) and not consumed_by_export(graph, node_id):
            issues.append(Issue("X_PATH", "%s produces nothing anyone reads" % node_id,
                                node=node_id, severity=WARNING,
                                hint="legal for a side effect; otherwise wire it onward"))

    seen = {}
    for node_id in graph.node_ids():
        node = graph.nodes[node_id]
        if node.tool is None:
            continue
        key = (node.tool, tuple(sorted(b.text() for b in node.ins)))
        if key in seen:
            issues.append(Issue("X_PATH", "%s repeats %s with the same inputs as %s"
                                % (node_id, node.tool, seen[key]), node=node_id,
                                severity=WARNING,
                                hint="one wasted environment interaction; reuse %s's output"
                                     % seen[key]))
        else:
            seen[key] = node_id
    return issues


def terminal_nodes(graph):
    out = set()
    for exports in graph.exports.values():
        for ref in exports.mapping.values():
            resolved = graph.resolve_ref(ref)
            if resolved:
                out.add(resolved[0])
    return out


def consumed_by_export(graph, node_id):
    for exports in graph.exports.values():
        for ref in exports.mapping.values():
            resolved = graph.resolve_ref(ref)
            if resolved and resolved[0] == node_id:
                return True
    return False


def check_state(graph, states):
    issues = []
    for node_id in graph.node_ids():
        state = states.get(node_id)
        if state is None or state.status != "failed":
            continue
        issues.append(Issue(state.error_class or "X_TOOL",
                            "%s already failed: %s" % (node_id, state.error), node=node_id,
                            hint="`atg blame` localizes it; `atg repair` fixes it locally"))
    return issues


def run_check(run, rev=None, strict=False, phase=None, graph=None, states=None):
    graph = graph if graph is not None else run.read_revision(rev)
    states = states if states is not None else run.node_states(graph)
    meta = run.meta()
    registry = run.registry()
    phase = phase or ("pre_exec" if not any(
        s.status != "pending" for s in states.values()) else "mid_exec")

    run.append_event("check_start", rev=graph.rev, src="cli", phase=phase)
    issues = []
    issues.extend(check_structure(graph, meta))
    issues.extend(check_tools(graph, registry))
    issues.extend(check_refs(graph, meta))
    issues.extend(check_types(graph, registry))
    issues.extend(check_state(graph, states))
    if strict:
        for issue in issues:
            issue.severity = BLOCKING
    issues.sort(key=lambda i: (0 if i.severity == BLOCKING else 1,
                               CLASSES.index(i.code) if i.code in CLASSES else 9,
                               id_sort_key(i.node) if i.node else (0,)))
    for issue in issues:
        run.append_event("check_issue", node=issue.node, rev=graph.rev, src="cli",
                         phase=phase, severity=issue.severity, msg=issue.message,
                         **{"class": issue.code})
    run.append_event("check_pass", rev=graph.rev, src="cli", phase=phase,
                     issue_count=len(issues),
                     blocking=len([i for i in issues if i.severity == BLOCKING]))
    return {"rev": graph.rev, "phase": phase, "issues": issues,
            "exit": worst_exit(issues)}


def add_issue(run, code, node, message, severity=BLOCKING, phase="pre_exec"):
    if code not in CLASSES:
        raise UsageError("unknown issue class %r" % code,
                         hint="one of: " + ", ".join(CLASSES))
    if severity not in SEVERITIES:
        raise UsageError("unknown severity %r" % severity,
                         hint="one of: " + ", ".join(SEVERITIES))
    graph = run.read_revision()
    if node is not None and node not in graph.nodes:
        raise NotFoundError("no node %s in %s" % (node, graph.rev),
                            hint="`atg show` lists the current graph")
    run.append_event("check_issue", node=node, rev=graph.rev, src="agent", phase=phase,
                     severity=severity, msg=message, **{"class": code})
    return {"class": code, "node": node, "msg": message, "severity": severity}


def confirm(run, node, would_have_failed):
    graph = run.read_revision()
    if node not in graph.nodes:
        raise NotFoundError("no node %s in %s" % (node, graph.rev),
                            hint="`atg show` lists the current graph")
    flagged = [r for r in run.events(("check_issue",)) if r.get("node") == node]
    if not flagged:
        raise UsageError("%s was never flagged by a check" % node,
                         hint="only flagged nodes can be confirmed; that is what makes "
                              "failure_precision honest")
    run.append_event("check_confirm", node=node, src="agent",
                     would_have_failed=bool(would_have_failed))
    return {"node": node, "would_have_failed": bool(would_have_failed)}


def issue_lines(issues):
    if not issues:
        return ["no issues"]
    out = []
    for issue in issues:
        out.append("%-8s %-10s %-6s %s" % (issue.severity, issue.code,
                                           issue.node or "-", issue.message))
        if issue.hint:
            out.append("         hint: %s" % issue.hint)
    return out
