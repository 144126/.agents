import argparse
import json
import os
import shutil
import sys

from . import __version__, FORMAT_VERSION
from . import check as checker
from . import compile as compiler
from . import execute, metrics, render as renderer, repair as repairer, schedule, selftest
from . import store, tools
from .dsl import parse_graph, serialize_graph
from .errors import (AtgError, EXIT_BLOCK, EXIT_OK, EXIT_USAGE, EXIT_WARN, NotFoundError,
                     UsageError, worst_exit)
from .model import ROOT_ID, is_node_id

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(SKILL_DIR, "templates")


def build_parser():
    parser = argparse.ArgumentParser(prog="atg", description="Atomic Task Graph engine")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--run", dest="run_id", metavar="ID", help="run id to operate on")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="start a run from a task statement")
    init.add_argument("task")
    init.add_argument("--out", dest="outputs", metavar="FIELD", action="append",
                      help="declared final output field (repeatable, default: answer)")
    init.add_argument("--input", dest="inputs", metavar="K=V", action="append",
                      help="value for $task.K (repeatable)")
    init.add_argument("--tools", metavar="FILE", help="tool registry to snapshot")
    init.add_argument("--acceptance", metavar="FILE", help="acceptance criteria file")
    init.add_argument("--budget", dest="budgets", metavar="K=V", action="append")
    init.add_argument("--run-id", dest="new_run_id", metavar="ID")

    sub.add_parser("status", help="phase, node states, next action")
    sub.add_parser("open", help="list nodes still lacking a tool: the worklist")
    sub.add_parser("history", help="list G_0…G_T with the node each refined")
    sub.add_parser("runs", help="list runs under the run root")

    show = sub.add_parser("show", help="print a revision")
    show.add_argument("--rev", metavar="G00x")

    context = sub.add_parser("context",
                             help="print exactly the context for refining a node")
    context.add_argument("id")
    context.add_argument("--repair", action="store_true",
                         help="add failure evidence and reusable outputs")

    refine = sub.add_parser("refine", help="replace a node with its subgraph")
    refine.add_argument("id")
    add_fragment_args(refine)
    refine.add_argument("--note", metavar="TEXT")

    check = sub.add_parser("check", help="thought experiment over the current plan")
    check.add_argument("--rev", metavar="G00x")
    check.add_argument("--strict", action="store_true",
                       help="promote warnings to blocking")
    check.add_argument("--add", dest="add", metavar="CLASS", choices=checker.CLASSES,
                       help="record an agent-found issue")
    check.add_argument("--node", metavar="ID")
    check.add_argument("--msg", metavar="TEXT")
    check.add_argument("--severity", choices=checker.SEVERITIES, default="blocking")
    check.add_argument("--confirm", nargs=2, metavar=("ID", "TRUE|FALSE"),
                       help="record whether a flagged node truly would have failed")

    sub.add_parser("ready", help="the executable frontier with resolved inputs")

    step = sub.add_parser("step", help="execute one frontier")
    add_exec_args(step)

    loop = sub.add_parser("run", help="loop step until done or blocked")
    add_exec_args(loop)
    loop.add_argument("--max-frontiers", type=int, metavar="N")
    loop.add_argument("--audit", action="store_true",
                      help="execute flagged nodes unrepaired and record whether they "
                           "really failed — the only honest source of failure_precision")

    execcmd = sub.add_parser("exec", help="execute the run: commands on the frontier")
    add_exec_args(execcmd)
    execcmd.add_argument("--dry-run", action="store_true",
                         help="print resolved commands without running them")

    done = sub.add_parser("done", help="record a node's output")
    done.add_argument("id")
    done.add_argument("--out", dest="outs", metavar="K=V", action="append", required=True,
                      help="V may be @file or - for stdin")

    fail = sub.add_parser("fail", help="record a node's failure")
    fail.add_argument("id")
    fail.add_argument("--err", required=True, metavar="TEXT")
    fail.add_argument("--class", dest="error_class", metavar="CLASS",
                      choices=checker.CLASSES)

    node = sub.add_parser("node", help="print a node's full record")
    node.add_argument("id")

    blame = sub.add_parser("blame",
                           help="localize failure, find the LCA, scope the repair")
    blame.add_argument("ids", nargs="*")

    repair = sub.add_parser("repair", help="replace a subgraph, freezing everything else")
    repair.add_argument("id")
    add_fragment_args(repair)
    repair.add_argument("--note", metavar="TEXT")

    sub.add_parser("metrics", help="fold the event log into the paper's numbers")
    sub.add_parser("report", help="write reports/report.md")

    render = sub.add_parser("render", help="draw the graph")
    render.add_argument("--as", dest="fmt", choices=renderer.FORMATS, default="ascii")
    render.add_argument("--rev", metavar="G00x")
    render.add_argument("--status", action="store_true", help="annotate with node state")
    render.add_argument("--history", action="store_true", help="render G_0…G_T instead")
    render.add_argument("-o", "--out", metavar="FILE", help="write to a file")

    toolcmd = sub.add_parser("tools", help="show, check or scaffold the tool registry")
    toolcmd.add_argument("--check", action="store_true")
    toolcmd.add_argument("--init", dest="scaffold", action="store_true",
                         help="copy the generic template into the run")

    fmt = sub.add_parser("fmt", help="canonicalize a .atg file")
    fmt.add_argument("file")
    fmt.add_argument("-w", "--write", action="store_true", help="rewrite in place")
    fmt.add_argument("--parent", metavar="ID",
                     help="treat the file as a refinement fragment of ID: local ids "
                          "like `node 1` and `$1.field` are expanded")

    test = sub.add_parser("selftest", help="run the built-in test suite")
    test.add_argument("-v", "--verbose", action="store_true")

    sub.add_parser("version", help="print version")
    return parser


def add_fragment_args(cmd):
    cmd.add_argument("--from-file", dest="from_file", metavar="FILE")
    cmd.add_argument("--from", dest="from_stdin", metavar="-", nargs="?", const="-")


def add_exec_args(cmd):
    cmd.add_argument("--jobs", type=int, metavar="N")
    cmd.add_argument("--timeout", type=int, default=execute.DEFAULT_TIMEOUT, metavar="S")
    cmd.add_argument("--blob-threshold", type=int, default=execute.BLOB_THRESHOLD,
                     metavar="BYTES")


def emit(args, data, lines, exit_code=EXIT_OK):
    if args.json:
        payload = dict(data)
        payload.setdefault("ok", exit_code in (EXIT_OK, EXIT_WARN))
        print(json.dumps(payload, sort_keys=True, default=str))
    else:
        text = lines if isinstance(lines, str) else "\n".join(lines)
        if text:
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return exit_code


def open_run(args):
    return store.resolve_run(args.run_id)


def read_fragment(args, what):
    if args.from_file and args.from_stdin:
        raise UsageError("pass either --from-file or --from -, not both")
    if args.from_file:
        with open(args.from_file, "r") as handle:
            return handle.read(), args.from_file
    if args.from_stdin:
        return sys.stdin.read(), "<stdin>"
    raise UsageError("%s needs a subgraph: --from-file plan.atg, or --from - for stdin"
                     % what,
                     hint="`atg context <id>` prints what the subgraph may consume "
                          "and must produce")


def parse_kv(pairs, what):
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise UsageError("%s %r must look like key=value" % (what, pair))
        key, value = pair.split("=", 1)
        out[key.strip()] = value
    return out


def read_out_value(value):
    if value == "-":
        return sys.stdin.read().rstrip("\n")
    if value.startswith("@"):
        with open(value[1:], "r") as handle:
            return handle.read().rstrip("\n")
    return value


def cmd_version(args):
    return emit(args, {"version": __version__, "format": FORMAT_VERSION},
                "atg %s (format atg/%d)" % (__version__, FORMAT_VERSION))


def cmd_selftest(args):
    return selftest.run(verbose=args.verbose)


def cmd_fmt(args):
    with open(args.file, "r") as handle:
        text = handle.read()
    if args.parent:
        if not is_node_id(args.parent):
            raise UsageError("--parent %r is not a node id" % args.parent,
                             hint="ids look like N0, N3, N3.2")
        body = compiler.normalize_fragment(text, args.parent)
    else:
        body = text if text.lstrip().startswith("# atg/") else "# atg/1\n\n" + text
    out = serialize_graph(parse_graph(body, args.file))
    if args.write:
        changed = out != text
        if changed:
            with open(args.file, "w") as handle:
                handle.write(out)
        return emit(args, {"file": args.file, "changed": changed},
                    "%s: %s" % (args.file,
                                "rewritten" if changed else "already canonical"))
    return emit(args, {"file": args.file, "text": out}, out)


def cmd_init(args):
    budgets = store.parse_budgets(args.budgets)
    acceptance = None
    if args.acceptance:
        with open(args.acceptance, "r") as handle:
            acceptance = handle.read()
    run = store.create_run(args.task, outputs=args.outputs, tools_path=args.tools,
                           acceptance=acceptance, budgets=budgets,
                           run_id=args.new_run_id,
                           inputs=parse_kv(args.inputs, "input"))
    meta = run.meta()
    lines = ["run %s" % run.id, "root %s: %s" % (ROOT_ID, meta["task"]),
             "outputs: %s" % ", ".join(meta["outputs"]),
             "next: `atg context %s`, write the decomposition, "
             "`atg refine %s --from-file plan.atg`" % (ROOT_ID, ROOT_ID)]
    if not os.path.isfile(run.tools_path):
        lines.append("note: no tool registry — `atg tools --init` scaffolds one "
                     "(tool checks stay warnings without it)")
    return emit(args, {"run": run.id, "path": run.path, "meta": meta}, lines)


def cmd_runs(args):
    rows = []
    for run in sorted(store.list_runs(), key=store.run_mtime, reverse=True):
        meta = run.meta()
        rows.append({"id": run.id, "status": meta.get("status"),
                     "task": meta.get("task")})
    lines = ["%-34s %-10s %s" % (r["id"], r["status"] or "-", r["task"] or "")
             for r in rows] or ["no runs under %s" % store.runs_root()]
    return emit(args, {"root": store.runs_root(), "runs": rows}, lines)


def cmd_status(args):
    run = open_run(args)
    graph = run.read_revision()
    states = run.node_states(graph)
    phase = store.phase_of(run, graph)
    report = schedule.ready_report(run, graph, states)
    counts = schedule.status_counts(states)
    lines = ["run %s   rev %s   phase %s" % (run.id, graph.rev, phase),
             "task: %s" % (graph.task or run.meta().get("task")),
             "nodes: %d (%s)" % (len(graph.nodes),
                                 ", ".join("%s=%d" % (k, counts[k])
                                           for k in sorted(counts))),
             "frontier: %d" % report["frontier"], ""]
    for node_id in graph.display_order():
        node = graph.nodes[node_id]
        lines.append("  %-8s %-11s %-14s %s" % (node_id, states[node_id].label(),
                                                node.tool or "(open)",
                                                compiler.short(node.goal, 46)))
    lines.append("")
    lines.append("next: " + next_action(graph, report, states, phase))
    data = {"run": run.id, "rev": graph.rev, "phase": phase,
            "frontier": report["frontier"], "counts": counts,
            "nodes": [dict(states[i].as_dict(), tool=graph.nodes[i].tool,
                           goal=graph.nodes[i].goal) for i in graph.display_order()],
            "ready": [n["id"] for n in report["nodes"]], "waiting": report["waiting"]}
    return emit(args, data, lines)


def next_action(graph, report, states, phase):
    if graph.open_nodes():
        target = graph.open_nodes()[0]
        return "`atg context %s` then `atg refine %s --from-file plan.atg`" % (target,
                                                                               target)
    failed = [i for i in graph.node_ids() if states[i].status == "failed"]
    if failed:
        return "`atg blame` (failed: %s)" % ", ".join(failed)
    if phase == "compiled":
        return "`atg check` before touching the environment"
    if report["nodes"]:
        return "`atg ready` then `atg step`"
    if phase == "done":
        return "`atg report`"
    return "`atg check` explains why nothing is runnable"


def cmd_open(args):
    run = open_run(args)
    graph = run.read_revision()
    ids = graph.open_nodes()
    lines = ["%-8s %s" % (i, graph.nodes[i].goal) for i in ids] or \
            ["compiled: every node is a single atomic tool-use unit"]
    return emit(args, {"rev": graph.rev, "open": ids, "compiled": not ids}, lines)


def cmd_show(args):
    run = open_run(args)
    graph = run.read_revision(args.rev)
    text = serialize_graph(graph)
    return emit(args, {"rev": graph.rev, "text": text}, text)


def cmd_history(args):
    run = open_run(args)
    rows = metrics.history_rows(run)
    lines = ["%-6s %-9s %-6s %s" % (r["rev"], r["refined"] or "-",
                                    r["kind"] or "refine", r["what"]) for r in rows]
    return emit(args, {"revisions": rows, "head": run.head()}, lines)


def cmd_context(args):
    run = open_run(args)
    data = compiler.context(run, args.id, repair=args.repair)
    return emit(args, data, compiler.context_text(data))


def cmd_refine(args):
    run = open_run(args)
    text, filename = read_fragment(args, "refine")
    result = compiler.refine(run, args.id, text, filename=filename, note=args.note)
    lines = ["%s → %s: replaced %s with %s" % (result["graph"].parent, result["rev"],
                                               args.id, ", ".join(result["added"]))]
    for issue in result["issues"]:
        lines.append("  %s %s: %s" % (issue["severity"], issue["class"], issue["msg"]))
    lines.append("next: " + ("`atg open` lists what is still coarse"
                             if result["graph"].open_nodes() else
                             "`atg check` — the plan is fully compiled"))
    payload = dict((k, v) for k, v in result.items() if k not in ("graph", "fragment"))
    return emit(args, payload, lines, EXIT_WARN if result["issues"] else EXIT_OK)


def cmd_check(args):
    run = open_run(args)
    if args.confirm:
        node, verdict = args.confirm
        if verdict.lower() not in ("true", "false"):
            raise UsageError("confirm takes true or false, got %r" % verdict)
        result = checker.confirm(run, node, verdict.lower() == "true")
        return emit(args, result, "recorded: %s would%s have failed"
                    % (node, "" if result["would_have_failed"] else " not"))
    if args.add:
        if not args.msg:
            raise UsageError("--add needs --msg \"what is wrong\"")
        result = checker.add_issue(run, args.add, args.node, args.msg, args.severity)
        return emit(args, result, "recorded %s %s on %s: %s"
                    % (result["severity"], result["class"], result["node"] or "-",
                       result["msg"]))
    result = checker.run_check(run, rev=args.rev, strict=args.strict)
    lines = ["check %s (%s): %d issue(s)" % (result["rev"], result["phase"],
                                             len(result["issues"]))]
    lines.extend(checker.issue_lines(result["issues"]))
    if result["exit"] == EXIT_OK:
        lines.append("next: `atg ready` then `atg step`")
    elif result["exit"] == EXIT_BLOCK:
        lines.append("next: fix every blocking issue by refining or repairing the named "
                     "nodes before touching the environment")
    payload = {"rev": result["rev"], "phase": result["phase"],
               "issues": [i.as_dict() for i in result["issues"]]}
    return emit(args, payload, lines, result["exit"])


def cmd_ready(args):
    run = open_run(args)
    report = schedule.ready_report(run)
    lines = ["frontier %d: %d ready" % (report["frontier"], len(report["nodes"]))]
    for entry in report["nodes"]:
        lines.append("  %-8s %-14s %s" % (entry["id"], entry["tool"] or "-",
                                          compiler.short(entry["goal"], 50)))
        for name in sorted(entry["in"]):
            lines.append("      %s = %s" % (name,
                                            compiler.short(entry["in"][name], 70)))
        lines.append("      out: %s" % (", ".join(entry["out"]) or "-"))
        if entry["run"]:
            lines.append("      run: %s" % compiler.short(entry["run"], 70))
    if report["waiting"]:
        lines.append("waiting:")
        for entry in report["waiting"]:
            lines.append("  %-8s %s" % (entry["id"], "; ".join(entry["why"])))
    return emit(args, report, lines)


def exec_lines(result):
    lines = ["frontier %d" % result["frontier"]]
    for entry in result["commands"]:
        lines.append("  would run %s (timeout %ss):" % (entry["id"], entry["timeout"]))
        for line in entry["cmd"].splitlines():
            lines.append("    " + line)
    for entry in result["results"]:
        if entry["status"] == "done":
            lines.append("  ✔ %-8s %sms  %s" % (entry["id"], entry["ms"],
                                                ", ".join(sorted(entry["out"]))))
        else:
            lines.append("  ✘ %-8s %sms  %s" % (entry["id"], entry["ms"], entry["err"]))
    for entry in result["manual"]:
        lines.append("  → %-8s needs you: %s (%s)"
                     % (entry["id"], entry["tool"] or "-",
                        compiler.short(entry["goal"], 44)))
    if result["manual"]:
        lines.append("  record each with `atg done <id> --out k=v` or "
                     "`atg fail <id> --err m`")
    return lines


def cmd_exec(args):
    run = open_run(args)
    result = execute.exec_frontier(run, jobs=args.jobs, timeout=args.timeout,
                                   dry_run=getattr(args, "dry_run", False),
                                   threshold=args.blob_threshold)
    failed = [r for r in result["results"] if r["status"] == "failed"]
    lines = exec_lines(result)
    if failed:
        lines.append("next: `atg blame` — %d node(s) failed" % len(failed))
    return emit(args, result, lines, EXIT_BLOCK if failed else EXIT_OK)


def cmd_run(args):
    run = open_run(args)
    result = execute.loop(run, jobs=args.jobs, timeout=args.timeout,
                          max_frontiers=args.max_frontiers,
                          threshold=args.blob_threshold, audit=args.audit)
    lines = []
    for step in result["steps"]:
        lines.extend(exec_lines(step))
    lines.append("status: %s after %d frontier(s)" % (result["status"],
                                                      len(result["steps"])))
    for field, value in sorted((result.get("outputs") or {}).items()):
        lines.append("  %s = %s" % (field, compiler.short(value, 70)))
    for entry in result.get("manual") or []:
        lines.append("  → %s needs you (%s)" % (entry["id"], entry["tool"] or "-"))
    for entry in result.get("waiting") or []:
        lines.append("  %-8s %s" % (entry["id"], "; ".join(entry["why"])))
    return emit(args, result, lines,
                EXIT_BLOCK if result["status"] == "blocked" else EXIT_OK)


def cmd_done(args):
    run = open_run(args)
    out = dict((k, read_out_value(v))
               for k, v in parse_kv(args.outs, "output").items())
    result = execute.mark_done(run, args.id, out)
    return emit(args, result, "done %s: %s" % (args.id, ", ".join(sorted(out))))


def cmd_fail(args):
    run = open_run(args)
    result = execute.mark_fail(run, args.id, args.err, args.error_class)
    return emit(args, result, ["failed %s: %s" % (args.id, args.err),
                               "next: `atg blame`"])


def cmd_node(args):
    run = open_run(args)
    graph = run.read_revision()
    node = compiler.live_node(graph, args.id)
    if node is None:
        raise NotFoundError("no node %s in %s" % (args.id, graph.rev),
                            hint="`atg show` lists the current graph")
    states = run.node_states(graph)
    state = states.get(args.id) or store.NodeState(args.id)
    history = [e for e in run.events() if e.get("node") == args.id]
    label = state.label() if args.id in graph.nodes else "refined away"
    lines = ["node %s   %s" % (args.id, label),
             "goal:  %s" % node.goal,
             "tool:  %s" % (node.tool or "(open)"),
             "in:    %s" % (", ".join(b.text() for b in node.ins) or "-"),
             "out:   %s" % (", ".join(node.outs) or "-"),
             "preds: %s" % (", ".join(graph.preds(args.id)) or "-"),
             "succs: %s" % (", ".join(graph.succs(args.id)) or "-")]
    if node.after:
        lines.append("after: %s" % ", ".join(node.after))
    if node.origin:
        lines.append("from:  %s" % node.origin)
    if args.id not in graph.nodes:
        lines.insert(1, "note:  this is the interface its subgraph must honour")
        lines.append("subgraph: %s" % ", ".join(
            "%s (%s)" % (i, states[i].label()) for i in compiler.scope_ids(graph, args.id)))
    for label, values in (("resolved inputs", state.inputs), ("outputs", state.output)):
        if values:
            lines.append("%s:" % label)
            for key in sorted(values):
                lines.append("  %s = %s" % (key, compiler.short(values[key], 70)))
    if state.error:
        lines.append("error: %s (%s)" % (state.error, state.error_class or "-"))
    lines.append("events:")
    for record in history:
        lines.append("  %s %-6s %s" % (record.get("t"), record.get("ev"),
                                       metrics.summary_of(record)))
    return emit(args, {"node": state.as_dict(), "goal": node.goal, "tool": node.tool,
                       "preds": graph.preds(args.id), "succs": graph.succs(args.id),
                       "events": history}, lines)


def cmd_blame(args):
    run = open_run(args)
    result = repairer.blame(run, args.ids or None)
    return emit(args, result, repairer.blame_lines(result),
                EXIT_WARN if result["issues"] else EXIT_OK)


def cmd_repair(args):
    run = open_run(args)
    text, filename = read_fragment(args, "repair")
    result = repairer.repair(run, args.id, text, filename=filename, note=args.note)
    lines = ["repaired %s → %s" % (args.id, result["rev"]),
             "added:   %s" % (", ".join(result["added"]) or "-"),
             "removed: %s" % (", ".join(result["removed"]) or "-"),
             "reused:  %s" % (", ".join(result["reused"]) or "-"),
             "stale:   %s" % (", ".join(result["stale"]) or "-"),
             "frozen:  %s" % (", ".join(result["frozen"]) or "-")]
    for issue in result["issues"]:
        lines.append("  %s %s: %s" % (issue["severity"], issue["class"], issue["msg"]))
    lines.append("next: `atg check` then `atg ready`")
    payload = dict((k, v) for k, v in result.items() if k not in ("graph", "fragment"))
    return emit(args, payload, lines, EXIT_WARN if result["issues"] else EXIT_OK)


def cmd_metrics(args):
    run = open_run(args)
    data = metrics.collect(run)
    return emit(args, data, metrics.metric_lines(data))


def cmd_report(args):
    run = open_run(args)
    graph = run.read_revision()
    states = run.node_states(graph)
    text = metrics.report(run, graph, states)
    if not os.path.isdir(run.reports_dir):
        os.makedirs(run.reports_dir)
    path = os.path.join(run.reports_dir, "report.md")
    with open(path, "w") as handle:
        handle.write(text)
    with open(os.path.join(run.reports_dir, "metrics.json"), "w") as handle:
        json.dump(metrics.collect(run, graph, states), handle, indent=2, sort_keys=True,
                  default=str)
        handle.write("\n")
    for fmt, ext in (("mermaid", "mmd"), ("dot", "dot"), ("ascii", "txt")):
        with open(os.path.join(run.reports_dir, "graph." + ext), "w") as handle:
            handle.write(renderer.render(graph, states, fmt, status=True))
    return emit(args, {"path": path, "reports": run.reports_dir},
                ["wrote %s" % path,
                 "also: metrics.json, graph.mmd, graph.dot, graph.txt"])


def cmd_render(args):
    run = open_run(args)
    if args.history:
        text = renderer.render_history(run, args.fmt)
    else:
        graph = run.read_revision(args.rev)
        states = run.node_states(graph)
        text = renderer.render(graph, states, args.fmt, status=args.status)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text)
        return emit(args, {"path": args.out, "format": args.fmt},
                    "wrote %s" % args.out)
    return emit(args, {"format": args.fmt, "text": text}, text)


def cmd_tools(args):
    if args.scaffold and not store.list_runs(store.runs_root()):
        target = os.path.join(os.getcwd(), "tools.atg")
        if os.path.isfile(target):
            raise UsageError("%s already exists" % target,
                             hint="edit it, then `atg init \"<task>\" --tools %s`" % target)
        shutil.copyfile(os.path.join(TEMPLATES, "tools.atg"), target)
        return emit(args, {"path": target},
                    ["copied the generic registry to %s" % target,
                     "edit it so it lists the tools you actually have, then "
                     "`atg init \"<task>\" --tools tools.atg`"])
    run = open_run(args)
    if args.scaffold:
        if os.path.isfile(run.tools_path):
            raise UsageError("%s already has a registry at %s" % (run.id,
                                                                 run.tools_path),
                             hint="edit it directly, or delete it first")
        shutil.copyfile(os.path.join(TEMPLATES, "tools.atg"), run.tools_path)
        return emit(args, {"path": run.tools_path},
                    ["copied the generic registry to %s" % run.tools_path,
                     "edit it so it lists the tools you actually have, then "
                     "`atg tools --check`"])
    registry = run.registry()
    issues = tools.check_registry(registry) if args.check else []
    lines = []
    for name in registry.names():
        spec = registry.tools[name]
        lines.append("%-14s %s" % (name, spec.desc or ""))
        lines.append("  in:  %s" % (", ".join(p.text() for p in spec.ins) or "(none)"))
        lines.append("  out: %s" % (", ".join(p.text() for p in spec.outs) or "(none)"))
    if not lines:
        lines.append("no registry at %s — `atg tools --init` scaffolds one"
                     % run.tools_path)
    for issue in issues:
        lines.append("%s %s: %s" % (issue.severity, issue.code, issue.message))
    payload = {"source": registry.source, "tools": registry.names(),
               "issues": [i.as_dict() for i in issues]}
    return emit(args, payload, lines, worst_exit(issues))


COMMANDS = {
    "init": cmd_init, "runs": cmd_runs, "status": cmd_status, "open": cmd_open,
    "show": cmd_show, "history": cmd_history, "context": cmd_context,
    "refine": cmd_refine, "check": cmd_check, "ready": cmd_ready, "exec": cmd_exec,
    "step": cmd_exec, "run": cmd_run, "done": cmd_done, "fail": cmd_fail,
    "node": cmd_node, "blame": cmd_blame, "repair": cmd_repair,
    "metrics": cmd_metrics, "report": cmd_report, "render": cmd_render,
    "tools": cmd_tools, "fmt": cmd_fmt, "selftest": cmd_selftest,
    "version": cmd_version,
}

NODE_ARG_COMMANDS = ("context", "refine", "node", "repair")


def check_ids(args):
    if args.command in NODE_ARG_COMMANDS and not is_node_id(args.id):
        raise UsageError("%r is not a node id" % args.id,
                         hint="ids look like N0, N1, N3.2")
    for node_id in getattr(args, "ids", []) or []:
        if not is_node_id(node_id):
            raise UsageError("%r is not a node id" % node_id,
                             hint="ids look like N0, N1, N3.2")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE
    try:
        check_ids(args)
        return COMMANDS[args.command](args)
    except AtgError as err:
        if args.json:
            print(json.dumps({"ok": False, "error": err.as_dict()}, sort_keys=True))
        else:
            sys.stderr.write(str(err) + "\n")
        return err.exit_code
    except (IOError, OSError) as err:
        if args.json:
            print(json.dumps({"ok": False,
                              "error": {"code": "E_IO", "message": str(err)}}))
        else:
            sys.stderr.write("E_IO: %s\n" % err)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
