import contextlib
import datetime
import json
import os
import re
import shutil
import time

from .dsl import parse_graph, serialize_graph
from .errors import AtgError, NotFoundError, UsageError
from .model import Graph, Node, Registry, ROOT_ID
from .tools import parse_registry

try:
    import fcntl
except ImportError:
    fcntl = None

DEFAULT_BUDGETS = {
    "max_depth": 5,
    "max_nodes": 200,
    "max_fanout": 8,
    "max_repairs_per_node": 3,
    "max_repairs_per_run": 10,
}

REV_RE = re.compile(r"^G(\d+)\.atg$")
SLUG_RE = re.compile(r"[^a-z0-9]+")
PENDING = "pending"


def utcnow():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (now.microsecond // 1000)


def slugify(text, limit=24):
    return SLUG_RE.sub("-", (text or "").lower()).strip("-")[:limit].strip("-") or "task"


def runs_root():
    return os.environ.get("ATG_DIR") or os.path.join(os.getcwd(), ".atg")


@contextlib.contextmanager
def locked(path):
    if fcntl is None:
        yield
        return
    handle = open(path, "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


class NodeState(object):
    __slots__ = ("id", "status", "frozen", "inputs", "output", "error", "error_class",
                 "ms", "frontier", "attempts")

    def __init__(self, node_id):
        self.id = node_id
        self.status = PENDING
        self.frozen = False
        self.inputs = {}
        self.output = {}
        self.error = None
        self.error_class = None
        self.ms = None
        self.frontier = None
        self.attempts = 0

    def as_dict(self):
        return {
            "id": self.id, "status": self.status, "frozen": self.frozen,
            "in": self.inputs, "out": self.output, "err": self.error,
            "err_class": self.error_class, "ms": self.ms, "frontier": self.frontier,
            "attempts": self.attempts,
        }

    def label(self):
        return "%s (frozen)" % self.status if self.frozen else self.status


class Run(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.id = os.path.basename(self.path)

    @property
    def meta_path(self):
        return os.path.join(self.path, "run.json")

    @property
    def events_path(self):
        return os.path.join(self.path, "events.jsonl")

    @property
    def head_path(self):
        return os.path.join(self.path, "HEAD")

    @property
    def graphs_dir(self):
        return os.path.join(self.path, "graphs")

    @property
    def tools_path(self):
        return os.path.join(self.path, "tools.atg")

    @property
    def task_path(self):
        return os.path.join(self.path, "task.md")

    @property
    def blobs_dir(self):
        return os.path.join(self.path, "blobs")

    @property
    def reports_dir(self):
        return os.path.join(self.path, "reports")

    def meta(self):
        with open(self.meta_path, "r") as handle:
            return json.load(handle)

    def save_meta(self, meta):
        with open(self.meta_path, "w") as handle:
            json.dump(meta, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def budgets(self):
        merged = dict(DEFAULT_BUDGETS)
        merged.update(self.meta().get("budgets", {}))
        return merged

    def head(self):
        with open(self.head_path, "r") as handle:
            return handle.read().strip()

    def set_head(self, rev):
        with open(self.head_path, "w") as handle:
            handle.write(rev + "\n")

    def revisions(self):
        if not os.path.isdir(self.graphs_dir):
            return []
        found = []
        for name in os.listdir(self.graphs_dir):
            match = REV_RE.match(name)
            if match:
                found.append((int(match.group(1)), name[:-4]))
        return [rev for _index, rev in sorted(found)]

    def revision_path(self, rev):
        return os.path.join(self.graphs_dir, rev + ".atg")

    def read_revision(self, rev=None):
        rev = rev or self.head()
        path = self.revision_path(rev)
        if not os.path.isfile(path):
            raise NotFoundError("no revision %s in run %s" % (rev, self.id),
                                hint="`atg history` lists the revisions that exist")
        with open(path, "r") as handle:
            return parse_graph(handle.read(), path)

    def next_rev(self):
        existing = self.revisions()
        return "G%03d" % (int(existing[-1][1:]) + 1 if existing else 0)

    def write_revision(self, graph, advance_head=True):
        rev = self.next_rev()
        graph.rev = rev
        if not graph.created:
            graph.created = utcnow()
        with open(self.revision_path(rev), "w") as handle:
            handle.write(serialize_graph(graph))
        if advance_head:
            self.set_head(rev)
        return rev

    def registry(self):
        if not os.path.isfile(self.tools_path):
            return Registry(source=None)
        with open(self.tools_path, "r") as handle:
            return parse_registry(handle.read(), self.tools_path)

    def next_seq(self):
        last = 0
        if os.path.isfile(self.events_path):
            with open(self.events_path, "r") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        try:
                            last = json.loads(line).get("seq", last)
                        except ValueError:
                            continue
        return last + 1

    def append_event(self, ev, node=None, rev=None, src="cli", **payload):
        with locked(self.meta_path):
            record = {"seq": self.next_seq(), "t": utcnow(),
                      "rev": rev or self._head_quiet(), "node": node, "ev": ev, "src": src}
            record.update(payload)
            with open(self.events_path, "a") as handle:
                handle.write(json.dumps(record) + "\n")
        return record

    def _head_quiet(self):
        try:
            return self.head()
        except (IOError, OSError):
            return None

    def events(self, kinds=None):
        if not os.path.isfile(self.events_path):
            return []
        out = []
        with open(self.events_path, "r") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if kinds is None or record.get("ev") in kinds:
                    out.append(record)
        out.sort(key=lambda r: r.get("seq", 0))
        return out

    def node_states(self, graph=None):
        graph = graph if graph is not None else self.read_revision()
        states = dict((node_id, NodeState(node_id)) for node_id in graph.nodes)
        for record in self.events():
            ev = record.get("ev")
            node_id = record.get("node")
            if ev in ("stale", "freeze", "prune") and record.get("nodes"):
                for target in record["nodes"]:
                    state = states.get(target)
                    if state is None:
                        continue
                    if ev == "freeze":
                        state.frozen = True
                    elif ev == "prune":
                        state.status = "skipped"
                    elif state.status in ("done", "failed", "running"):
                        state.status = "stale"
                continue
            state = states.get(node_id)
            if state is None:
                continue
            if ev == "start":
                state.status = "running"
                state.attempts += 1
                state.inputs = record.get("in", state.inputs)
                state.frontier = record.get("frontier", state.frontier)
            elif ev == "done":
                state.status = "done"
                state.output = record.get("out", {})
                state.error = None
                state.error_class = None
                state.ms = record.get("ms", state.ms)
                state.frontier = record.get("frontier", state.frontier)
            elif ev == "fail":
                state.status = "failed"
                state.error = record.get("err")
                state.error_class = record.get("class")
                state.ms = record.get("ms", state.ms)
                state.frontier = record.get("frontier", state.frontier)
        return states

    def __repr__(self):
        return "Run(%s)" % self.id


def list_runs(root=None):
    root = root or runs_root()
    if not os.path.isdir(root):
        return []
    found = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isfile(os.path.join(path, "run.json")):
            found.append(Run(path))
    return found


def run_mtime(run):
    stamps = []
    for path in (run.events_path, run.meta_path):
        if os.path.isfile(path):
            stamps.append(os.path.getmtime(path))
    return max(stamps) if stamps else 0


def resolve_run(run_id=None, root=None):
    root = root or runs_root()
    run_id = run_id or os.environ.get("ATG_RUN")
    if run_id:
        path = os.path.join(root, run_id)
        if not os.path.isfile(os.path.join(path, "run.json")):
            raise NotFoundError("no run %r under %s" % (run_id, root),
                                code="E_NO_RUN",
                                hint="`atg init \"<task>\"` starts one")
        return Run(path)
    runs = list_runs(root)
    if not runs:
        raise NotFoundError("no ATG run found under %s" % root, code="E_NO_RUN",
                            hint="`atg init \"<task>\"` starts one; $ATG_DIR moves the root")
    return max(runs, key=run_mtime)


def parse_budgets(pairs):
    budgets = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise UsageError("budget %r must look like key=value" % pair,
                             hint="known budgets: " + ", ".join(sorted(DEFAULT_BUDGETS)))
        key, value = pair.split("=", 1)
        key = key.strip()
        if key not in DEFAULT_BUDGETS:
            raise UsageError("unknown budget %r" % key,
                             hint="known budgets: " + ", ".join(sorted(DEFAULT_BUDGETS)))
        try:
            budgets[key] = int(value)
        except ValueError:
            raise UsageError("budget %s must be a whole number, got %r" % (key, value))
        if budgets[key] < 1:
            raise UsageError("budget %s must be at least 1" % key)
    return budgets


def create_run(task, outputs=None, tools_path=None, acceptance=None, budgets=None,
               run_id=None, root=None, inputs=None):
    root = root or runs_root()
    outputs = list(outputs or ["answer"])
    run_id = run_id or "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), slugify(task))
    path = os.path.join(root, run_id)
    if os.path.exists(path):
        raise AtgError("run %r already exists at %s" % (run_id, path),
                       hint="pass --run-id to name a different one")
    for sub in ("", "graphs", "blobs", "reports"):
        os.makedirs(os.path.join(path, sub))
    run = Run(path)

    if tools_path:
        shutil.copyfile(tools_path, run.tools_path)

    with open(run.task_path, "w") as handle:
        handle.write("# task\n\n%s\n" % task.strip())
        if acceptance:
            handle.write("\n# acceptance criteria\n\n%s\n" % acceptance.strip())

    root_node = Node(ROOT_ID, goal=task.strip(), outs=outputs)
    graph = Graph(task=task.strip(), nodes={ROOT_ID: root_node})
    rev = run.write_revision(graph)

    run.save_meta({
        "id": run_id,
        "task": task.strip(),
        "created": utcnow(),
        "cwd": os.getcwd(),
        "outputs": outputs,
        "inputs": dict(inputs or {}),
        "budgets": dict(budgets or {}),
        "status": "compiling",
    })
    run.append_event("init", rev=rev, task=task.strip(), outputs=outputs,
                     inputs=dict(inputs or {}), budgets=dict(budgets or {}),
                     tools=bool(tools_path))
    return run


def phase_of(run, graph=None):
    graph = graph if graph is not None else run.read_revision()
    if graph.open_nodes():
        return "compiling"
    states = run.node_states(graph)
    statuses = set(state.status for state in states.values())
    if statuses == set(["done"]) and states:
        return "done"
    if statuses & set(["running", "done", "failed", "stale"]):
        return "blocked" if "failed" in statuses else "executing"
    return "compiled"
