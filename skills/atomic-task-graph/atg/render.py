from .errors import UsageError
from .model import id_sort_key
from .schedule import levels

FORMATS = ("mermaid", "dot", "ascii", "md")
GLYPHS = {"done": "✔", "failed": "✘", "running": "▸", "pending": "·", "stale": "~",
          "skipped": "-"}
CLASS_STYLE = (
    ("done", "fill:#d7f0d7,stroke:#2f7a2f,color:#123312"),
    ("failed", "fill:#f7d6d6,stroke:#a12626,color:#3d0f0f"),
    ("running", "fill:#d8e6ff,stroke:#2b5fa8,color:#0f2340"),
    ("stale", "fill:#fdf0cf,stroke:#a3811f,color:#3a2e07"),
    ("frozen", "fill:#e9e9ef,stroke:#6b6b7b,color:#23232b"),
    ("pending", "fill:#ffffff,stroke:#8a8a8a,color:#222222"),
    ("open", "fill:#ffffff,stroke:#8a8a8a,stroke-dasharray:4 3,color:#222222"),
)


def state_class(graph, states, node_id):
    state = states.get(node_id) if states else None
    if not graph.nodes[node_id].is_atomic:
        return "open"
    if state is None:
        return "pending"
    if state.frozen and state.status == "done":
        return "frozen"
    return state.status if state.status in dict(CLASS_STYLE) else "pending"


def escape_label(text, limit=54):
    text = (text or "").replace('"', "'").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def mermaid(graph, states, status):
    lines = ["flowchart TD"]
    for node_id in graph.display_order():
        node = graph.nodes[node_id]
        parts = [node_id, escape_label(node.goal)]
        if node.tool:
            parts.append("[%s]" % node.tool)
        if status and states:
            state = states.get(node_id)
            if state is not None:
                parts.append("%s %s" % (GLYPHS.get(state.status, "?"), state.label()))
        shape = '("%s")' if not node.is_atomic else '["%s"]'
        lines.append("  %s%s" % (safe_id(node_id), shape % "<br/>".join(parts)))
    for src, dst, field, kind in sorted(graph.edges(),
                                        key=lambda e: (id_sort_key(e[0]),
                                                       id_sort_key(e[1]))):
        arrow = "-.->" if kind == "after" else "-->"
        label = "|%s|" % field if field and kind == "data" else ("|after|" if
                                                                kind == "after" else "")
        lines.append("  %s %s%s %s" % (safe_id(src), arrow, label, safe_id(dst)))
    if status and states:
        for name, style in CLASS_STYLE:
            lines.append("  classDef %s %s" % (name, style))
        for name, _style in CLASS_STYLE:
            members = [safe_id(i) for i in graph.display_order()
                       if state_class(graph, states, i) == name]
            if members:
                lines.append("  class %s %s" % (",".join(members), name))
    return "\n".join(lines) + "\n"


def safe_id(node_id):
    return node_id.replace(".", "_")


def dot(graph, states, status):
    lines = ["digraph atg {", "  rankdir=TB;",
             '  node [shape=box, fontname="Helvetica"];']
    for node_id in graph.display_order():
        node = graph.nodes[node_id]
        label = "\\n".join([node_id, escape_label(node.goal)]
                           + (["[%s]" % node.tool] if node.tool else []))
        attrs = ['label="%s"' % label]
        if not node.is_atomic:
            attrs.append("style=dashed")
        if status and states:
            state = states.get(node_id)
            if state is not None:
                attrs.append('xlabel="%s"' % state.label())
        lines.append("  %s [%s];" % (safe_id(node_id), ", ".join(attrs)))
    for src, dst, field, kind in sorted(graph.edges(),
                                        key=lambda e: (id_sort_key(e[0]),
                                                       id_sort_key(e[1]))):
        attrs = ['label="%s"' % (field or "after")]
        if kind == "after":
            attrs.append("style=dotted")
        lines.append("  %s -> %s [%s];" % (safe_id(src), safe_id(dst), ", ".join(attrs)))
    lines.append("}")
    return "\n".join(lines) + "\n"


def ascii_art(graph, states, status):
    rank = graph.topo_rank()
    rows = {}
    for node_id in graph.node_ids():
        rows.setdefault(rank.get(node_id, 0), []).append(node_id)
    done_levels = levels(graph, states) if states else {}
    lines = []
    for level in sorted(rows):
        cells = []
        for node_id in sorted(rows[level], key=id_sort_key):
            node = graph.nodes[node_id]
            glyph = " "
            if status and states and node_id in states:
                glyph = GLYPHS.get(states[node_id].status, "?")
            cells.append("%s %-4s %s" % (glyph, node_id,
                                         escape_label(node.tool or node.goal, 28)))
        lines.append("rank %d" % level)
        for cell in cells:
            lines.append("  ┌" + "─" * (len(cell) + 2) + "┐")
            lines.append("  │ " + cell + " │")
            lines.append("  └" + "─" * (len(cell) + 2) + "┘")
        if level != max(rows):
            lines.append("        │")
            lines.append("        ▼")
    if done_levels:
        lines.append("")
        lines.append("completed frontiers: %d" % (1 + max(done_levels.values())))
    edge_lines = ["%s → %s%s" % (s, d, (" (%s)" % f) if f else " (after)")
                  for s, d, f, _k in sorted(graph.edges(),
                                            key=lambda e: (id_sort_key(e[0]),
                                                           id_sort_key(e[1])))]
    if edge_lines:
        lines.append("")
        lines.append("edges: " + "; ".join(edge_lines))
    return "\n".join(lines) + "\n"


def markdown(graph, states, status):
    lines = ["| node | goal | tool | in | out | status |", "|---|---|---|---|---|---|"]
    for node_id in graph.display_order():
        node = graph.nodes[node_id]
        state = states.get(node_id) if states else None
        lines.append("| `%s` | %s | %s | %s | %s | %s |" % (
            node_id, escape_label(node.goal, 60), node.tool or "_(open)_",
            ", ".join("`%s`" % b.text() for b in node.ins) or "-",
            ", ".join(node.outs) or "-",
            state.label() if (state and status) else "-"))
    lines.append("")
    lines.append("**edges**")
    for src, dst, field, kind in sorted(graph.edges(),
                                        key=lambda e: (id_sort_key(e[0]),
                                                       id_sort_key(e[1]))):
        lines.append("- `%s` → `%s` (%s%s)" % (src, dst, field or "control",
                                               ", after" if kind == "after" else ""))
    for node_id in sorted(graph.exports, key=id_sort_key):
        lines.append("")
        lines.append("**exports %s**" % node_id)
        mapping = graph.exports[node_id].mapping
        for field in sorted(mapping):
            lines.append("- `%s` = `%s`" % (field, mapping[field].text()))
    return "\n".join(lines) + "\n"


RENDERERS = {"mermaid": mermaid, "dot": dot, "ascii": ascii_art, "md": markdown}


def render(graph, states, fmt, status=False):
    if fmt not in RENDERERS:
        raise UsageError("unknown render format %r" % fmt,
                         hint="one of: " + ", ".join(FORMATS))
    return RENDERERS[fmt](graph, states, status)


def render_history(run, fmt):
    from .metrics import history_rows

    rows = history_rows(run)
    if fmt == "mermaid":
        lines = ["flowchart LR"]
        for index, row in enumerate(rows):
            lines.append('  %s["%s<br/>%s"]' % (row["rev"], row["rev"], row["what"]))
            if index:
                lines.append("  %s --> %s" % (rows[index - 1]["rev"], row["rev"]))
        return "\n".join(lines) + "\n"
    if fmt == "md":
        lines = ["| revision | refined | kind | nodes |", "|---|---|---|---|"]
        for row in rows:
            lines.append("| `%s` | %s | %s | %d |" % (row["rev"], row["refined"] or "-",
                                                      row["kind"] or "refine",
                                                      row["nodes"]))
        return "\n".join(lines) + "\n"
    lines = []
    for row in rows:
        lines.append("%-6s %s" % (row["rev"], row["what"]))
    return "\n".join(lines) + "\n"
