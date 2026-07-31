import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import time

from .errors import NotFoundError, UsageError
from .model import ROOT_ID, id_sort_key
from .schedule import frontier_index, is_blocked, ready_report, resolve_inputs

REF_RE = re.compile(r"\$(N\d+(?:\.\d+)*|task|env)\.([A-Za-z_][A-Za-z0-9_]*)")
BLOB_THRESHOLD = 8192
DEFAULT_TIMEOUT = 120
MAX_JOBS = 8


def blob_path(run, value):
    digest = hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16]
    path = os.path.join(run.blobs_dir, digest + ".txt")
    if not os.path.isfile(path):
        if not os.path.isdir(run.blobs_dir):
            os.makedirs(run.blobs_dir)
        with open(path, "w") as handle:
            handle.write(value)
    return path


def spill(run, value, threshold=BLOB_THRESHOLD):
    text = value if isinstance(value, str) else json.dumps(value)
    if len(text) <= threshold:
        return text
    return blob_path(run, text)


def resolve_command(run, graph, states, meta, node_id, threshold=BLOB_THRESHOLD):
    node = graph.nodes[node_id]
    values, missing = resolve_inputs(graph, states, meta, node_id)
    if missing:
        raise UsageError("%s still has unresolved inputs: %s" % (node_id, ", ".join(missing)),
                         hint="`atg ready` lists what can run now")
    text = node.run or ""

    def substitute(match):
        ref = "$%s.%s" % (match.group(1), match.group(2))
        for binding in node.ins:
            if hasattr(binding.value, "target") and binding.value.text() == ref:
                return spill(run, values[binding.name], threshold)
        return match.group(0)

    resolved = REF_RE.sub(substitute, text)
    for name, value in values.items():
        resolved = resolved.replace("${%s}" % name, spill(run, value, threshold))
    return resolved, values


def outputs_from_stdout(node, stdout):
    text = stdout.strip()
    if not node.outs:
        return {}, None
    parsed = None
    if text.startswith("{"):
        try:
            candidate = json.loads(text)
        except ValueError:
            candidate = None
        if isinstance(candidate, dict):
            parsed = candidate
    if parsed is not None and set(parsed) & set(node.outs):
        return dict((f, stringify(parsed.get(f, ""))) for f in node.outs), None
    if len(node.outs) == 1:
        return {node.outs[0]: text}, None
    return {}, ("%s declares %d outputs, so its stdout must be a JSON object with keys %s"
                % (node.id, len(node.outs), ", ".join(node.outs)))


def stringify(value):
    return value if isinstance(value, str) else json.dumps(value)


def run_one(command, timeout):
    started = time.time()
    try:
        done = subprocess.run(command, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
        code, stdout, stderr = (done.returncode,
                                done.stdout.decode("utf-8", "replace"),
                                done.stderr.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired:
        code, stdout, stderr = (124, "", "timed out after %ss" % timeout)
    return code, stdout, stderr, int((time.time() - started) * 1000)


def record_done(run, node_id, out, ms=None, frontier=None, src="exec", note=None,
                threshold=BLOB_THRESHOLD):
    payload = dict((k, spill(run, v, threshold)) for k, v in (out or {}).items())
    return run.append_event("done", node=node_id, src=src, out=payload, ms=ms,
                            frontier=frontier, note=note)


def record_fail(run, node_id, err, error_class=None, ms=None, frontier=None, src="exec"):
    return run.append_event("fail", node=node_id, src=src, err=err,
                            **{"class": error_class, "ms": ms, "frontier": frontier})


def mark_done(run, node_id, out, src="agent"):
    graph = run.read_revision()
    if node_id not in graph.nodes:
        raise NotFoundError("no node %s in %s" % (node_id, graph.rev),
                            hint="`atg show` lists the current graph")
    node = graph.nodes[node_id]
    unknown = [f for f in out if f not in node.outs]
    if unknown and node.outs:
        raise UsageError("%s does not declare output %s" % (node_id, ", ".join(unknown)),
                         hint="declared outputs: " + (", ".join(node.outs) or "(none)"))
    missing = [f for f in node.outs if f not in out]
    if missing:
        raise UsageError("%s must report every declared output; missing %s"
                         % (node_id, ", ".join(missing)),
                         hint="atg done %s --out %s"
                              % (node_id, ",".join("%s=..." % f for f in node.outs)))
    states = run.node_states(graph)
    frontier = frontier_index(graph, states)
    record_done(run, node_id, out, frontier=frontier, src=src)
    return {"node": node_id, "out": list(out), "frontier": frontier}


def mark_fail(run, node_id, err, error_class=None, src="agent"):
    graph = run.read_revision()
    if node_id not in graph.nodes:
        raise NotFoundError("no node %s in %s" % (node_id, graph.rev),
                            hint="`atg show` lists the current graph")
    states = run.node_states(graph)
    frontier = frontier_index(graph, states)
    record_fail(run, node_id, err, error_class, frontier=frontier, src=src)
    return {"node": node_id, "err": err, "class": error_class, "frontier": frontier}


def exec_frontier(run, jobs=None, timeout=DEFAULT_TIMEOUT, dry_run=False,
                  threshold=BLOB_THRESHOLD, graph=None, states=None):
    graph = graph if graph is not None else run.read_revision()
    states = states if states is not None else run.node_states(graph)
    meta = run.meta()
    report = ready_report(run, graph, states)
    frontier = report["frontier"]
    runnable = [n for n in report["nodes"] if n["run"]]
    manual = [n for n in report["nodes"] if not n["run"]]

    plan = []
    for entry in runnable:
        command, _values = resolve_command(run, graph, states, meta, entry["id"], threshold)
        plan.append((entry["id"], command, entry["timeout"] or timeout))
    if dry_run:
        return {"frontier": frontier, "dry_run": True,
                "commands": [{"id": i, "cmd": c, "timeout": t} for i, c, t in plan],
                "manual": manual, "results": [], "blocked": is_blocked(report, states)}

    for node_id, command, _t in plan:
        run.append_event("start", node=node_id, src="exec", frontier=frontier,
                         cmd=command)

    width = max(1, len(plan))
    results = []
    if plan:
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=jobs or min(MAX_JOBS, width)) as pool:
            futures = dict((pool.submit(run_one, command, node_timeout), node_id)
                           for node_id, command, node_timeout in plan)
            for future in concurrent.futures.as_completed(futures):
                results.append((futures[future], future.result()))
    results.sort(key=lambda item: id_sort_key(item[0]))

    finished = []
    for node_id, (code, stdout, stderr, ms) in results:
        node = graph.nodes[node_id]
        if code != 0:
            message = (stderr.strip() or stdout.strip() or "exit %d" % code)
            record_fail(run, node_id, message, "X_TOOL", ms=ms, frontier=frontier)
            finished.append({"id": node_id, "status": "failed", "err": message, "ms": ms})
            continue
        out, problem = outputs_from_stdout(node, stdout)
        if problem:
            record_fail(run, node_id, problem, "X_IFACE", ms=ms, frontier=frontier)
            finished.append({"id": node_id, "status": "failed", "err": problem, "ms": ms})
            continue
        record_done(run, node_id, out, ms=ms, frontier=frontier, threshold=threshold)
        finished.append({"id": node_id, "status": "done",
                         "out": dict((k, spill(run, v, threshold)) for k, v in out.items()),
                         "ms": ms})
    after = run.node_states(graph)
    return {"frontier": frontier, "dry_run": False, "commands": [],
            "manual": manual, "results": finished,
            "blocked": is_blocked(ready_report(run, graph, after), after)}


def loop(run, jobs=None, timeout=DEFAULT_TIMEOUT, max_frontiers=None,
         threshold=BLOB_THRESHOLD, audit=False):
    steps = []
    limit = max_frontiers or 100
    while len(steps) < limit:
        graph = run.read_revision()
        states = run.node_states(graph)
        report = ready_report(run, graph, states)
        if not report["nodes"]:
            return finish(run, graph, states, steps, report)
        if not any(n["run"] for n in report["nodes"]):
            return {"status": "waiting_on_agent", "steps": steps,
                    "manual": report["nodes"], "frontier": report["frontier"]}
        steps.append(exec_frontier(run, jobs, timeout, graph=graph, states=states,
                                   threshold=threshold))
        if audit:
            audit_frontier(run, steps[-1])
        if steps[-1]["results"] and any(r["status"] == "failed" for r in steps[-1]["results"]):
            graph = run.read_revision()
            states = run.node_states(graph)
            return finish(run, graph, states, steps, ready_report(run, graph, states))
    return {"status": "max_frontiers", "steps": steps}


def audit_frontier(run, step):
    flagged = set(r.get("node") for r in run.events(("check_issue",))
                  if r.get("severity") == "blocking" and r.get("node"))
    confirmed = set(r.get("node") for r in run.events(("check_confirm",)))
    for result in step["results"]:
        if result["id"] not in flagged or result["id"] in confirmed:
            continue
        run.append_event("check_confirm", node=result["id"], src="audit",
                         would_have_failed=result["status"] == "failed",
                         note="observed by `atg run --audit`")


def finish(run, graph, states, steps, report):
    status = "blocked" if is_blocked(report, states) else "done"
    outputs = final_outputs(run, graph, states)
    run.append_event("finish", src="cli", status=status, outputs=outputs)
    meta = run.meta()
    meta["status"] = status
    run.save_meta(meta)
    return {"status": status, "steps": steps, "outputs": outputs,
            "waiting": report["waiting"]}


def final_outputs(run, graph, states):
    out = {}
    exports = graph.exports.get(ROOT_ID)
    declared = run.meta().get("outputs") or []
    for field in declared:
        ref = exports.mapping.get(field) if exports else None
        if ref is None:
            continue
        resolved = graph.resolve_ref(ref)
        if resolved is None:
            continue
        state = states.get(resolved[0])
        if state is not None and state.status == "done":
            out[field] = state.output.get(resolved[1])
    return out
