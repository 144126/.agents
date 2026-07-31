import re

from .dsl import parse_graph
from .errors import (BudgetError, FrozenError, Issue, NotFoundError, UsageError, WARNING,
                     raise_if_blocking)
from .model import (ROOT_ID, Binding, Node, Ref, id_depth, id_parent, id_sort_key,
                    id_subtree, is_descendant)

LOCAL_ID_RE = re.compile(r"^\d+(\.\d+)*$")
LOCAL_REF_RE = re.compile(r"\$(\d+(?:\.\d+)*)\.")
BLOCK_LINE_RE = re.compile(r"^(node|exports)[ \t]+(\S+)[ \t]*$")
FIELD_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
OPAQUE_FIELDS = ("run", "goal", "note")


def qualify(parent_id, local):
    return ("N" + local) if parent_id == ROOT_ID else "%s.%s" % (parent_id, local)


def normalize_fragment(text, parent_id):
    lines = []
    has_header = False
    field = None
    in_heredoc = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if in_heredoc:
            lines.append(raw)
            if stripped == ">>>":
                in_heredoc = False
            continue
        if stripped.startswith("# atg/"):
            has_header = True
            lines.append(raw)
            continue
        block = BLOCK_LINE_RE.match(stripped)
        if block:
            field = None
            if LOCAL_ID_RE.match(block.group(2)):
                raw = "%s %s" % (block.group(1), qualify(parent_id, block.group(2)))
            lines.append(raw)
            continue
        named = FIELD_LINE_RE.match(stripped)
        if named:
            field = named.group(1)
        if stripped.endswith("<<<"):
            in_heredoc = True
        if field not in OPAQUE_FIELDS:
            raw = LOCAL_REF_RE.sub(lambda m: "$%s." % qualify(parent_id, m.group(1)), raw)
        lines.append(raw)
    body = "\n".join(lines)
    if not has_header:
        body = "# atg/1\n\n" + body
    return body


def parse_fragment(text, parent_id, filename="<fragment>"):
    return parse_graph(normalize_fragment(text, parent_id), filename)


def free_refs(fragment, parent_id):
    internal = set(fragment.nodes) | set(
        i for i in fragment.exports if is_descendant(i, parent_id))
    out = []
    for node_id in fragment.node_ids():
        for ref in fragment.nodes[node_id].refs():
            if ref.is_special or ref.target in internal:
                continue
            out.append((node_id, ref))
    return out


def live_node(graph, node_id):
    if node_id in graph.nodes:
        return graph.nodes[node_id]
    subtree = id_subtree(graph.nodes, node_id)
    if not subtree:
        return None
    inside = set(subtree)
    ins = []
    seen = set()
    for target in subtree:
        for binding in graph.nodes[target].ins:
            if not isinstance(binding.value, Ref) or binding.value.is_special:
                continue
            resolved = graph.resolve_ref(binding.value)
            if resolved is not None and resolved[0] in inside:
                continue
            text = binding.value.text()
            if text in seen:
                continue
            seen.add(text)
            ins.append(Binding(binding.name, binding.value))
    exports = graph.exports.get(node_id)
    return Node(node_id, goal="(refined away; interface reconstructed)", ins=ins,
                outs=sorted(exports.mapping) if exports else [])


def check_interface(base, fragment, parent_id, merged, removed):
    parent = live_node(base, parent_id)
    issues = []
    allowed_refs = set(r.text() for r in parent.refs())
    reachable = set(base.ancestors(parent_id))

    for node_id, ref in free_refs(fragment, parent_id):
        if ref.target == parent_id:
            issues.append(Issue("E_IFACE_SELF",
                                "%s refers to %s, the node being replaced" % (node_id,
                                                                              ref.text()),
                                node=node_id,
                                hint="a subgraph cannot consume its own parent's output"))
            continue
        if ref.text() in allowed_refs:
            continue
        target = merged.resolve_ref(ref)
        if target is not None and target[0] in reachable:
            continue
        issues.append(Issue("E_IFACE_INPUT",
                            "%s reads %s, which is not an input of %s"
                            % (node_id, ref.text(), parent_id),
                            node=node_id,
                            hint="allowed: %s, $task.*, $env.*, or any ancestor of %s"
                                 % (", ".join(sorted(allowed_refs)) or "(none)", parent_id)))

    exports = fragment.exports.get(parent_id)
    mapping = exports.mapping if exports else {}
    for field in parent.outs:
        if field not in mapping:
            issues.append(Issue("E_IFACE_OUTPUT",
                                "no export binds %s.%s" % (parent_id, field),
                                node=parent_id,
                                hint="add:\nexports %s\n  %s = $<inner-node>.%s"
                                     % (parent_id, field, field)))
            continue
        target = merged.resolve_ref(mapping[field])
        if target is None or target[0] not in fragment.nodes:
            issues.append(Issue("E_IFACE_OUTPUT",
                                "export %s.%s = %s does not resolve to a node in the subgraph"
                                % (parent_id, field, mapping[field].text()),
                                node=parent_id,
                                hint="point it at one of: " + ", ".join(fragment.node_ids())))
    for field in sorted(mapping):
        if field not in parent.outs:
            issues.append(Issue("W_IFACE_WIDE",
                                "export %s.%s was not declared as an output of %s"
                                % (parent_id, field, parent_id),
                                node=parent_id, severity=WARNING,
                                hint="harmless, but nothing consumes it yet"))

    for node_id in sorted(fragment.nodes, key=id_sort_key):
        if not is_descendant(node_id, parent_id):
            issues.append(Issue("E_IFACE_SCOPE",
                                "%s is not inside %s" % (node_id, parent_id), node=node_id,
                                hint="name the children %s or plain 1, 2, 3"
                                     % qualify(parent_id, "1")))
        elif node_id in base.nodes and node_id not in removed:
            issues.append(Issue("E_IFACE_SCOPE",
                                "%s already exists outside the replaced subtree" % node_id,
                                node=node_id, hint="pick unused ids"))
    for node_id in fragment.exports:
        if node_id != parent_id and not is_descendant(node_id, parent_id):
            issues.append(Issue("E_IFACE_SCOPE",
                                "exports %s is outside %s" % (node_id, parent_id),
                                node=node_id))
    return issues


def check_orphans(fragment, parent_id):
    export_targets = set()
    exports = fragment.exports.get(parent_id)
    if exports:
        for ref in exports.mapping.values():
            resolved = fragment.resolve_ref(ref)
            if resolved:
                export_targets.add(resolved[0])
    _pred, succ = fragment.adjacency()
    useful = set(export_targets)
    changed = True
    while changed:
        changed = False
        for node_id in fragment.nodes:
            if node_id not in useful and succ[node_id] & useful:
                useful.add(node_id)
                changed = True
    issues = []
    for node_id in fragment.node_ids():
        if node_id not in useful:
            issues.append(Issue("W_ORPHAN",
                                "%s feeds nothing exported by %s" % (node_id, parent_id),
                                node=node_id, severity=WARNING,
                                hint="legal for a pure side effect; otherwise wire its "
                                     "output onward"))
    return issues


def check_budgets(run, base, fragment, parent_id, is_repair):
    budgets = run.budgets()
    fanout = len(fragment.nodes)
    if fanout > budgets["max_fanout"]:
        raise BudgetError("refining %s into %d nodes exceeds max_fanout=%d"
                          % (parent_id, fanout, budgets["max_fanout"]),
                          hint="decompose in two rounds, or raise the budget at init")
    depth = max(id_depth(i) for i in fragment.nodes)
    if depth > budgets["max_depth"]:
        raise BudgetError("%s reaches depth %d, over max_depth=%d"
                          % (parent_id, depth, budgets["max_depth"]),
                          hint="the nodes at this level are probably already atomic")
    total = len(base.nodes) - len(scope_ids(base, parent_id)) + fanout
    if total > budgets["max_nodes"]:
        raise BudgetError("the graph would hold %d nodes, over max_nodes=%d"
                          % (total, budgets["max_nodes"]),
                          hint="the plan is too fine-grained; coarsen it")
    if is_repair:
        counts = repair_counts(run)
        if counts["total"] >= budgets["max_repairs_per_run"]:
            raise BudgetError("this run has used all %d repairs"
                              % budgets["max_repairs_per_run"],
                              hint="escalate: replan from the root, or abort and report")
        if counts["per_node"].get(parent_id, 0) >= budgets["max_repairs_per_node"]:
            raise BudgetError("%s has been repaired %d times already"
                              % (parent_id, counts["per_node"][parent_id]),
                              hint="escalate one level: repair %s instead"
                                   % (id_parent(parent_id) or ROOT_ID))


def repair_counts(run):
    per_node = {}
    total = 0
    for record in run.events(("repair_applied",)):
        node = record.get("node") or record.get("lca")
        per_node[node] = per_node.get(node, 0) + 1
        total += 1
    return {"total": total, "per_node": per_node}


def splice(base, fragment, parent_id):
    merged = base.copy()
    removed = [parent_id] + id_subtree(base.nodes, parent_id)
    for node_id in removed:
        merged.nodes.pop(node_id, None)
    for node_id in list(merged.exports):
        if is_descendant(node_id, parent_id) or node_id == parent_id:
            del merged.exports[node_id]
    for node_id, node in fragment.nodes.items():
        merged.nodes[node_id] = node.copy()
    for node_id, exports in fragment.exports.items():
        merged.exports[node_id] = exports.copy()
    return merged, removed


def refine(run, parent_id, text, filename="<fragment>", kind=None, note=None,
           allow_atomic=False, frozen=None, src="agent"):
    base = run.read_revision()
    parent = live_node(base, parent_id)
    if parent is None:
        raise NotFoundError("no node %s in %s" % (parent_id, base.rev or "HEAD"),
                            hint="`atg show` lists the current graph")
    if parent.is_atomic and not allow_atomic:
        raise UsageError("%s is already atomic (tool: %s)" % (parent_id, parent.tool),
                         hint="only nodes without a tool: need refining; `atg open` "
                              "lists them")
    fragment = parse_fragment(text, parent_id, filename)
    if not fragment.nodes:
        raise UsageError("the subgraph for %s declares no nodes" % parent_id,
                         hint="write at least one 'node 1' block")

    if frozen:
        for node_id in sorted(set(fragment.nodes) | set(fragment.exports), key=id_sort_key):
            if node_id in frozen:
                raise FrozenError("%s is frozen: it holds a validated result outside the "
                                  "repair scope" % node_id,
                                  hint="repair only touches %s and its descendants"
                                       % parent_id)

    check_budgets(run, base, fragment, parent_id, is_repair=bool(kind == "repair"))
    merged, removed = splice(base, fragment, parent_id)

    issues = check_interface(base, fragment, parent_id, merged, set(removed))
    issues.extend(check_orphans(fragment, parent_id))
    fragment.topo_order()
    raise_if_blocking(issues, "%s does not preserve the interface of %s"
                      % (filename, parent_id),
                      hint="`atg context %s` prints exactly what it may consume and "
                           "must produce" % parent_id)
    merged.topo_order()

    merged.parent = base.rev
    merged.refined = parent_id
    merged.kind = kind
    merged.note = note
    merged.created = None
    rev = run.write_revision(merged)
    added = fragment.node_ids()
    run.append_event("refine", node=parent_id, rev=rev, src=src,
                     added=added, removed=[i for i in removed if i != parent_id],
                     depth=max(id_depth(i) for i in fragment.nodes))
    return {"rev": rev, "node": parent_id, "added": added,
            "removed": [i for i in removed if i != parent_id],
            "issues": [i.as_dict() for i in issues], "graph": merged,
            "fragment": fragment}


def interface_of(graph, node_id):
    node = live_node(graph, node_id)
    return {"id": node_id, "goal": node.goal, "tool": node.tool,
            "in": [b.text() for b in node.ins], "out": list(node.outs),
            "after": list(node.after)}


def context(run, node_id, repair=False, graph=None, states=None):
    graph = graph if graph is not None else run.read_revision()
    node = live_node(graph, node_id)
    if node is None:
        raise NotFoundError("no node %s in %s" % (node_id, graph.rev or "HEAD"),
                            hint="`atg show` lists the current graph")
    meta = run.meta()
    budgets = run.budgets()
    registry = run.registry()
    data = {
        "run": run.id,
        "rev": graph.rev,
        "task": meta.get("task"),
        "acceptance": read_acceptance(run),
        "inputs": meta.get("inputs", {}),
        "final_outputs": meta.get("outputs", []),
        "node": interface_of(graph, node_id),
        "predecessors": [interface_of(graph, i) for i in graph.preds(node_id)],
        "successors": [interface_of(graph, i) for i in graph.succs(node_id)],
        "tools": [{"name": n, "desc": registry.tools[n].desc,
                   "in": [p.text() for p in registry.tools[n].ins],
                   "out": [p.text() for p in registry.tools[n].outs]}
                  for n in registry.names()],
        "budget_left": {
            "depth": budgets["max_depth"] - id_depth(node_id),
            "nodes": budgets["max_nodes"] - len(graph.nodes),
            "fanout": budgets["max_fanout"],
        },
    }
    if repair:
        states = states if states is not None else run.node_states(graph)
        failures = []
        for target in scope_ids(graph, node_id):
            state = states.get(target)
            if state is not None and state.status == "failed":
                failures.append({"id": target, "goal": graph.nodes[target].goal,
                                 "err": state.error, "class": state.error_class,
                                 "in": state.inputs})
        data["failures"] = failures
        data["reusable"] = dict(
            ("%s.%s" % (target, field), value)
            for target in scope_ids(graph, node_id)
            for field, value in (states[target].output or {}).items()
            if target in states and states[target].status == "done")
        data["boundary"] = boundary_values(graph, states, node_id)
    return data


def scope_ids(graph, node_id):
    ids = id_subtree(graph.nodes, node_id)
    return ([node_id] + ids) if node_id in graph.nodes else ids


def boundary_values(graph, states, node_id):
    inside = set(scope_ids(graph, node_id))
    out = {}
    for target in sorted(inside, key=id_sort_key):
        for ref in graph.nodes[target].refs():
            resolved = graph.resolve_ref(ref)
            if resolved is None or resolved[0] in inside:
                continue
            state = states.get(resolved[0])
            if state is not None and state.status == "done":
                out[ref.text()] = state.output.get(resolved[1])
    return out


def read_acceptance(run):
    try:
        with open(run.task_path, "r") as handle:
            text = handle.read()
    except (IOError, OSError):
        return None
    marker = "# acceptance criteria"
    if marker not in text:
        return None
    return text.split(marker, 1)[1].strip() or None


def context_text(data):
    lines = ["# context for %s  (run %s, %s)" % (data["node"]["id"], data["run"],
                                                 data["rev"])]
    lines.append("")
    lines.append("task: %s" % data["task"])
    if data["acceptance"]:
        lines.append("acceptance:")
        for line in data["acceptance"].splitlines():
            lines.append("  " + line)
    if data["inputs"]:
        lines.append("task inputs: " + ", ".join(
            "$task.%s = %r" % (k, v) for k, v in sorted(data["inputs"].items())))
    if data["final_outputs"]:
        lines.append("final outputs: " + ", ".join(data["final_outputs"]))
    lines.append("")
    lines.append("## this node")
    lines.extend(iface_lines(data["node"]))
    for label, key in (("predecessors (interface only)", "predecessors"),
                       ("successors (interface only)", "successors")):
        lines.append("")
        lines.append("## %s" % label)
        if not data[key]:
            lines.append("  (none)")
        for iface in data[key]:
            lines.extend(iface_lines(iface))
    lines.append("")
    lines.append("## tool space")
    if not data["tools"]:
        lines.append("  (no registry — declare one with `atg tools --init`)")
    for tool in data["tools"]:
        lines.append("  %s: %s" % (tool["name"], tool["desc"] or ""))
        lines.append("    in:  %s" % (", ".join(tool["in"]) or "(none)"))
        lines.append("    out: %s" % (", ".join(tool["out"]) or "(none)"))
    if "failures" in data:
        lines.append("")
        lines.append("## failure evidence")
        for failure in data["failures"] or [{"id": "(none)", "err": None}]:
            lines.append("  %s: %s" % (failure["id"], failure.get("err")))
            if failure.get("in"):
                lines.append("    inputs: %s" % failure["in"])
        lines.append("")
        lines.append("## reusable verified outputs")
        for key in sorted(data["reusable"]):
            lines.append("  %s = %s" % (key, short(data["reusable"][key])))
        lines.append("")
        lines.append("## read-only boundary values")
        for key in sorted(data["boundary"]):
            lines.append("  %s = %s" % (key, short(data["boundary"][key])))
    left = data["budget_left"]
    lines.append("")
    lines.append("## budget left")
    lines.append("  depth %s, nodes %s, fanout %s per refinement"
                 % (left["depth"], left["nodes"], left["fanout"]))
    return "\n".join(lines) + "\n"


def iface_lines(iface):
    lines = ["  %s  %s" % (iface["id"], iface["goal"] or "")]
    if iface["tool"]:
        lines.append("    tool: %s" % iface["tool"])
    lines.append("    in:   %s" % (", ".join(iface["in"]) or "(none)"))
    lines.append("    out:  %s" % (", ".join(iface["out"]) or "(none)"))
    if iface["after"]:
        lines.append("    after: %s" % ", ".join(iface["after"]))
    return lines


def short(value, limit=120):
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + "…"
