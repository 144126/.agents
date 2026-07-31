import datetime

from .model import id_depth, id_sort_key
from .schedule import frontier_widths, levels, status_counts

HALLUCINATORY_CLASSES = ("X_TOOL", "X_DEP")


def parse_time(text):
    if not text:
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return None


def wall_ms(events):
    stamps = [parse_time(e.get("t")) for e in events]
    stamps = [s for s in stamps if s is not None]
    if len(stamps) < 2:
        return 0
    return int((max(stamps) - min(stamps)).total_seconds() * 1000)


def ratio(numerator, denominator):
    return None if not denominator else round(float(numerator) / denominator, 4)


def collect(run, graph=None, states=None):
    graph = graph if graph is not None else run.read_revision()
    states = states if states is not None else run.node_states(graph)
    events = run.events()
    by_kind = {}
    for record in events:
        by_kind.setdefault(record.get("ev"), []).append(record)

    executions = by_kind.get("done", []) + by_kind.get("fail", [])
    real_executions = [e for e in executions if e.get("src") != "reuse"]
    failures = by_kind.get("fail", [])
    hallucinatory = [e for e in failures if e.get("class") in HALLUCINATORY_CLASSES]

    done_levels = levels(graph, states)
    steps = 1 + max(done_levels.values()) if done_levels else 0
    serial_steps = len([e for e in by_kind.get("done", []) if e.get("src") != "reuse"])

    checks = by_kind.get("check_pass", [])
    pre_checks = [c for c in checks if c.get("phase") == "pre_exec"]
    risky = [c for c in pre_checks if c.get("blocking")]

    confirms = by_kind.get("check_confirm", [])
    confirmed_true = len([c for c in confirms if c.get("would_have_failed")])

    repairs = by_kind.get("repair_applied", [])
    repair_success, repair_total = repair_outcomes(run, events, repairs)

    reused = len([e for e in by_kind.get("done", []) if e.get("src") == "reuse"])
    pruned = sum(len(e.get("nodes") or []) for e in by_kind.get("prune", []))
    frozen_not_rerun = len(set(
        n for e in by_kind.get("freeze", []) for n in (e.get("nodes") or [])
        if n in states and states[n].status == "done"))

    counts = status_counts(states)
    return {
        "run": run.id,
        "rev": graph.rev,
        "revisions": len(run.revisions()),
        "nodes": len(graph.nodes),
        "max_depth": max([id_depth(i) for i in graph.nodes] or [0]),
        "open_nodes": len(graph.open_nodes()),
        "status_counts": counts,
        "steps": steps,
        "serial_steps": serial_steps,
        "parallel_saving": None if not serial_steps else round(
            1.0 - float(steps) / serial_steps, 4),
        "frontier_widths": frontier_widths(graph, states),
        "executions": len(real_executions),
        "failures": len(failures),
        "hallucinatory_actions": len(hallucinatory),
        "hallucinatory_action_rate": ratio(len(hallucinatory), len(real_executions)),
        "hallucinatory_trajectory": bool(hallucinatory),
        "checks_pre_exec": len(pre_checks),
        "risky_plans_detected": ratio(len(risky), len(pre_checks)),
        "flagged_nodes": len(set(e.get("node") for e in by_kind.get("check_issue", [])
                                 if e.get("node"))),
        "confirmations": len(confirms),
        "failure_precision": (ratio(confirmed_true, len(confirms)) if confirms
                              else "n/a"),
        "repairs": len(repairs),
        "repair_success_rate": ratio(repair_success, repair_total),
        "reused_outputs": reused,
        "pruned_nodes": pruned,
        "frozen_not_rerun": frozen_not_rerun,
        "saved_environment_interactions": reused + pruned + frozen_not_rerun,
        "wall_ms": wall_ms(events),
        "exec_ms": sum(e.get("ms") or 0 for e in executions),
    }


def repair_outcomes(run, events, repairs):
    if not repairs:
        return 0, 0
    live = set(run.read_revision().nodes)
    success = 0
    for record in repairs:
        seq = record.get("seq", 0)
        broken = set(e.get("node") for e in events
                     if e.get("ev") == "fail" and e.get("seq", 0) < seq)
        healed = True
        for node_id in broken:
            later = [e for e in events
                     if e.get("node") == node_id and e.get("seq", 0) > seq
                     and e.get("ev") in ("done", "fail")]
            if later:
                healed = healed and later[-1].get("ev") == "done"
            else:
                healed = healed and node_id not in live
        if healed:
            success += 1
    return success, len(repairs)


LABELS = (
    ("run", "run"),
    ("rev", "revision"),
    ("revisions", "revisions (G_0…G_T)"),
    ("nodes", "nodes"),
    ("open_nodes", "nodes still non-atomic"),
    ("max_depth", "max refinement depth"),
    ("steps", "steps (parallel frontiers)"),
    ("serial_steps", "serial steps (node completions)"),
    ("parallel_saving", "parallel saving"),
    ("frontier_widths", "frontier widths"),
    ("executions", "executions"),
    ("failures", "failures"),
    ("hallucinatory_action_rate", "hallucinatory action rate"),
    ("hallucinatory_trajectory", "hallucinatory trajectory"),
    ("checks_pre_exec", "pre-execution checks"),
    ("risky_plans_detected", "risky plans detected"),
    ("flagged_nodes", "nodes flagged risky"),
    ("failure_precision", "failure precision"),
    ("repairs", "repairs applied"),
    ("repair_success_rate", "repair success rate"),
    ("reused_outputs", "reused verified outputs"),
    ("pruned_nodes", "pruned nodes"),
    ("frozen_not_rerun", "frozen, not re-run"),
    ("saved_environment_interactions", "saved environment interactions"),
    ("wall_ms", "wall time (ms)"),
    ("exec_ms", "execution time (ms)"),
)


def metric_lines(data):
    out = []
    for key, label in LABELS:
        value = data.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) or "-"
        if value is None:
            value = "n/a"
        out.append("%-32s %s" % (label, value))
    counts = data.get("status_counts") or {}
    out.append("%-32s %s" % ("node status", ", ".join(
        "%s=%d" % (k, counts[k]) for k in sorted(counts)) or "-"))
    return out


def report(run, graph=None, states=None):
    from .execute import final_outputs
    from .render import render

    graph = graph if graph is not None else run.read_revision()
    states = states if states is not None else run.node_states(graph)
    data = collect(run, graph, states)
    meta = run.meta()
    lines = ["# ATG run report — %s" % run.id, "",
             "**task:** %s" % meta.get("task"), "",
             "## metrics", "", "| metric | value |", "|---|---|"]
    for key, label in LABELS:
        value = data.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) or "-"
        lines.append("| %s | %s |" % (label, "n/a" if value is None else value))
    lines.extend(["", "## final graph (%s)" % graph.rev, "", "```mermaid",
                  render(graph, states, "mermaid", status=True).rstrip(), "```", ""])
    lines.extend(["## refinement history", ""])
    for entry in history_rows(run):
        lines.append("- **%s** — %s" % (entry["rev"], entry["what"]))
    lines.extend(["", "## execution timeline", ""])
    for record in run.events(("done", "fail", "repair_applied", "stale", "prune",
                              "finish")):
        lines.append("- `%s` %s %s %s" % (record.get("t"), record.get("ev"),
                                          record.get("node") or "",
                                          summary_of(record)))
    lines.extend(["", "## outputs", ""])
    outputs = final_outputs(run, graph, states)
    for field in sorted(outputs):
        lines.append("- **%s**: %s" % (field, outputs[field]))
    if not outputs:
        lines.append("(no final output recorded yet)")
    return "\n".join(lines) + "\n"


def summary_of(record):
    if record.get("ev") == "fail":
        return "%s — %s" % (record.get("class") or "", record.get("err") or "")
    if record.get("ev") == "done":
        return ", ".join(sorted((record.get("out") or {}).keys()))
    if record.get("ev") == "repair_applied":
        return "added %s, reused %s" % (", ".join(record.get("added") or []),
                                        ", ".join(record.get("reused") or []) or "none")
    if record.get("nodes"):
        return ", ".join(record["nodes"])
    if record.get("ev") == "finish":
        return record.get("status") or ""
    return ""


def history_rows(run):
    added_by_rev = dict((e.get("rev"), e.get("added") or [])
                        for e in run.events(("refine",)))
    rows = []
    for rev in run.revisions():
        graph = run.read_revision(rev)
        if graph.refined:
            what = "refined %s%s → %s" % (
                graph.refined, " (repair)" if graph.kind == "repair" else "",
                ", ".join(sorted(added_by_rev.get(rev, []), key=id_sort_key))
                or "no new nodes")
        else:
            what = "initial graph, %d node(s)" % len(graph.nodes)
        rows.append({"rev": rev, "refined": graph.refined, "kind": graph.kind,
                     "nodes": len(graph.nodes), "what": what, "note": graph.note})
    return rows
