import re

from .errors import AtgError, CycleError

ROOT_ID = "N0"
ID_RE = re.compile(r"^N\d+(\.\d+)*$")
SPECIAL_TARGETS = ("task", "env")
FIELD_ORDER = ("goal", "tool", "in", "out", "after", "run", "timeout", "from", "note")


def is_node_id(text):
    return bool(ID_RE.match(text))


def id_parts(node_id):
    if not is_node_id(node_id):
        raise AtgError("not a node id: %r" % node_id, code="E_DSL_BAD_ID")
    return tuple(int(p) for p in node_id[1:].split("."))


def id_sort_key(node_id):
    return id_parts(node_id)


def id_depth(node_id):
    return 0 if node_id == ROOT_ID else len(id_parts(node_id))


def id_child(parent_id, index):
    if parent_id == ROOT_ID:
        return "N%d" % index
    return "%s.%d" % (parent_id, index)


def id_parent(node_id):
    if node_id == ROOT_ID:
        return None
    if "." not in node_id:
        return ROOT_ID
    return node_id.rsplit(".", 1)[0]


def is_descendant(node_id, ancestor_id):
    if ancestor_id == ROOT_ID:
        return node_id != ROOT_ID
    return node_id.startswith(ancestor_id + ".")


def common_ancestor(node_ids):
    ids = [i for i in node_ids if i != ROOT_ID]
    if not ids:
        return ROOT_ID
    parts = [id_parts(i) for i in ids]
    shared = []
    for column in zip(*parts):
        first = column[0]
        if all(v == first for v in column):
            shared.append(first)
        else:
            break
    if not shared:
        return ROOT_ID
    return "N" + ".".join(str(p) for p in shared)


class Ref(object):
    __slots__ = ("target", "field")

    def __init__(self, target, field):
        self.target = target
        self.field = field

    @property
    def is_special(self):
        return self.target in SPECIAL_TARGETS

    def text(self):
        return "$%s.%s" % (self.target, self.field)

    def __eq__(self, other):
        return (isinstance(other, Ref) and other.target == self.target
                and other.field == self.field)

    def __hash__(self):
        return hash((self.target, self.field))

    def __repr__(self):
        return "Ref(%s)" % self.text()


class Lit(object):
    __slots__ = ("raw", "kind")

    def __init__(self, raw, kind):
        self.raw = raw
        self.kind = kind

    def text(self):
        if self.kind == "str":
            return '"%s"' % escape_string(self.raw)
        if self.kind == "heredoc":
            return "<<<\n%s\n>>>" % self.raw
        return self.raw

    def __eq__(self, other):
        return isinstance(other, Lit) and other.raw == self.raw and other.kind == self.kind

    def __hash__(self):
        return hash((self.raw, self.kind))

    def __repr__(self):
        return "Lit(%r, %s)" % (self.raw, self.kind)


def escape_string(raw):
    return raw.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Binding(object):
    __slots__ = ("name", "value")

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def text(self):
        return "%s = %s" % (self.name, self.value.text())

    def __eq__(self, other):
        return (isinstance(other, Binding) and other.name == self.name
                and other.value == self.value)

    def __repr__(self):
        return "Binding(%s)" % self.text()


class Node(object):
    __slots__ = ("id", "goal", "tool", "ins", "outs", "after", "run", "timeout",
                 "origin", "note", "line")

    def __init__(self, node_id, goal="", tool=None, ins=None, outs=None, after=None,
                 run=None, timeout=None, origin=None, note=None, line=None):
        self.id = node_id
        self.goal = goal
        self.tool = tool
        self.ins = list(ins or [])
        self.outs = list(outs or [])
        self.after = list(after or [])
        self.run = run
        self.timeout = timeout
        self.origin = origin
        self.note = note
        self.line = line

    @property
    def is_atomic(self):
        return self.tool is not None

    def refs(self):
        return [b.value for b in self.ins if isinstance(b.value, Ref)]

    def binding(self, name):
        for b in self.ins:
            if b.name == name:
                return b
        return None

    def copy(self):
        return Node(self.id, self.goal, self.tool, [Binding(b.name, b.value) for b in self.ins],
                    list(self.outs), list(self.after), self.run, self.timeout,
                    self.origin, self.note, self.line)

    def __repr__(self):
        return "Node(%s, tool=%r)" % (self.id, self.tool)


class Exports(object):
    __slots__ = ("node_id", "mapping", "line")

    def __init__(self, node_id, mapping=None, line=None):
        self.node_id = node_id
        self.mapping = dict(mapping or {})
        self.line = line

    def copy(self):
        return Exports(self.node_id, dict(self.mapping), self.line)

    def __repr__(self):
        return "Exports(%s, %d fields)" % (self.node_id, len(self.mapping))


class Graph(object):
    def __init__(self, rev=None, parent=None, refined=None, kind=None, created=None,
                 note=None, task=None, nodes=None, exports=None, format_version=1):
        self.rev = rev
        self.parent = parent
        self.refined = refined
        self.kind = kind
        self.created = created
        self.note = note
        self.task = task
        self.format_version = format_version
        self.nodes = dict(nodes or {})
        self.exports = dict(exports or {})

    def copy(self):
        return Graph(self.rev, self.parent, self.refined, self.kind, self.created,
                     self.note, self.task,
                     dict((k, v.copy()) for k, v in self.nodes.items()),
                     dict((k, v.copy()) for k, v in self.exports.items()),
                     self.format_version)

    def node_ids(self):
        return sorted(self.nodes, key=id_sort_key)

    def open_nodes(self):
        return [i for i in self.node_ids() if not self.nodes[i].is_atomic]

    def resolve_ref(self, ref):
        if ref.is_special:
            return None
        target, field = ref.target, ref.field
        seen = set()
        while True:
            if target in self.nodes:
                return (target, field)
            exp = self.exports.get(target)
            if exp is None or field not in exp.mapping:
                return None
            key = (target, field)
            if key in seen:
                return None
            seen.add(key)
            nxt = exp.mapping[field]
            target, field = nxt.target, nxt.field

    def edges(self):
        out = []
        for node_id in self.node_ids():
            node = self.nodes[node_id]
            for ref in node.refs():
                resolved = self.resolve_ref(ref)
                if resolved is None:
                    continue
                src, field = resolved
                if src != node_id:
                    out.append((src, node_id, field, "data"))
            for src in node.after:
                if src in self.nodes and src != node_id:
                    out.append((src, node_id, None, "after"))
        return out

    def adjacency(self):
        succ = dict((i, set()) for i in self.nodes)
        pred = dict((i, set()) for i in self.nodes)
        for src, dst, _field, _kind in self.edges():
            succ[src].add(dst)
            pred[dst].add(src)
        return pred, succ

    def preds(self, node_id):
        pred, _succ = self.adjacency()
        return sorted(pred.get(node_id, ()), key=id_sort_key)

    def succs(self, node_id):
        _pred, succ = self.adjacency()
        return sorted(succ.get(node_id, ()), key=id_sort_key)

    def topo_order(self):
        pred, succ = self.adjacency()
        indegree = dict((i, len(pred[i])) for i in self.nodes)
        frontier = sorted([i for i, d in indegree.items() if d == 0], key=id_sort_key)
        order = []
        while frontier:
            node_id = frontier.pop(0)
            order.append(node_id)
            for nxt in sorted(succ[node_id], key=id_sort_key):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    frontier.append(nxt)
            frontier.sort(key=id_sort_key)
        if len(order) != len(self.nodes):
            stuck = sorted(set(self.nodes) - set(order), key=id_sort_key)
            raise CycleError("graph contains a cycle among %s" % ", ".join(stuck),
                             nodes=stuck,
                             hint="remove one of the $refs or after: entries closing the loop")
        return order

    def topo_rank(self):
        try:
            order = self.topo_order()
        except CycleError:
            return dict((i, 0) for i in self.nodes)
        pred, _succ = self.adjacency()
        rank = {}
        for node_id in order:
            parents = pred[node_id]
            rank[node_id] = 0 if not parents else 1 + max(rank[p] for p in parents)
        return rank

    def display_order(self):
        rank = self.topo_rank()
        return sorted(self.nodes, key=lambda i: (rank.get(i, 0), id_sort_key(i)))

    def produced_fields(self):
        out = {}
        for node_id, node in self.nodes.items():
            for field in node.outs:
                out[(node_id, field)] = node_id
        return out

    def __repr__(self):
        return "Graph(rev=%s, %d nodes)" % (self.rev, len(self.nodes))


class Param(object):
    __slots__ = ("name", "type", "required")

    def __init__(self, name, type_name=None, required=False):
        self.name = name
        self.type = type_name
        self.required = required

    def text(self):
        out = self.name
        if self.type:
            out += ":" + self.type
        if self.required:
            out += "!"
        return out

    def __repr__(self):
        return "Param(%s)" % self.text()


class ToolSpec(object):
    __slots__ = ("name", "desc", "ins", "outs", "line")

    def __init__(self, name, desc=None, ins=None, outs=None, line=None):
        self.name = name
        self.desc = desc
        self.ins = list(ins or [])
        self.outs = list(outs or [])
        self.line = line

    def param(self, name):
        for p in self.ins:
            if p.name == name:
                return p
        return None

    def required_params(self):
        return [p.name for p in self.ins if p.required]

    def output_names(self):
        return [p.name for p in self.outs]

    def __repr__(self):
        return "ToolSpec(%s)" % self.name


class Registry(object):
    def __init__(self, tools=None, source=None):
        self.tools = dict(tools or {})
        self.source = source

    @property
    def is_empty(self):
        return not self.tools

    def get(self, name):
        return self.tools.get(name)

    def names(self):
        return sorted(self.tools)

    def __repr__(self):
        return "Registry(%d tools)" % len(self.tools)
