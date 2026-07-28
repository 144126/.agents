import re

from . import FORMAT_VERSION
from .errors import DslError
from .model import (Binding, Exports, Graph, Lit, Node, Ref, escape_string,
                    id_sort_key, is_node_id, SPECIAL_TARGETS)

HEADER_RE = re.compile(r"^#\s*atg/(\d+)\s*(.*)$")
KV_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("(?:[^"\\]|\\.)*"|\S+)')
BLOCK_RE = re.compile(r"^([a-z_]+)[ \t]+(\S+)[ \t]*$")
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(.*)$")
LEADING_TAB_RE = re.compile(r"^[ ]*\t")
BARE_RE = re.compile(r"^[A-Za-z0-9_./:@+-]+$")
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOOL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

HEREDOC_OPEN = "<<<"
HEREDOC_CLOSE = ">>>"
BLOCK_INDENT = 2
LABEL_WIDTH = 6
WRAP_WIDTH = 88

NODE_FIELDS = ("goal", "tool", "in", "out", "after", "run", "timeout", "from", "note")
TEXT_FIELDS = ("goal", "note", "run")


class Block(object):
    __slots__ = ("kind", "name", "line", "fields")

    def __init__(self, kind, name, line):
        self.kind = kind
        self.name = name
        self.line = line
        self.fields = []

    def field_map(self, filename):
        out = {}
        for name, value, line in self.fields:
            if name in out:
                raise DslError("duplicate field %r in %s %s" % (name, self.kind, self.name),
                               code="E_DSL_DUP_FIELD", filename=filename, line=line,
                               hint="each field may appear once per block")
            out[name] = (value, line)
        return out


class Document(object):
    __slots__ = ("format_version", "header", "top_fields", "blocks", "filename")

    def __init__(self, format_version, header, top_fields, blocks, filename):
        self.format_version = format_version
        self.header = header
        self.top_fields = top_fields
        self.blocks = blocks
        self.filename = filename

    def top(self, name):
        for field_name, value, _line in self.top_fields:
            if field_name == name:
                return value
        return None


def strip_comment(line):
    out = []
    in_string = False
    index = 0
    while index < len(line):
        char = line[index]
        if in_string:
            if char == "\\" and index + 1 < len(line):
                out.append(char)
                out.append(line[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            out.append(char)
        else:
            if char == '"':
                in_string = True
                out.append(char)
            elif char == "#":
                break
            else:
                out.append(char)
        index += 1
    return "".join(out).rstrip()


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def parse_document(text, filename="<string>", require_header=True):
    raw_lines = text.splitlines()
    index = 0
    format_version = FORMAT_VERSION
    header = {}

    while index < len(raw_lines) and not raw_lines[index].strip():
        index += 1
    if index < len(raw_lines):
        match = HEADER_RE.match(raw_lines[index].strip())
        if match:
            format_version = int(match.group(1))
            for key, value in KV_RE.findall(match.group(2)):
                header[key] = unquote_header(value)
            index += 1
        elif require_header:
            raise DslError("missing '# atg/%d' header line" % FORMAT_VERSION,
                           filename=filename, line=index + 1,
                           text=raw_lines[index],
                           hint="the first non-blank line must look like: # atg/1 rev=G000")

    top_fields = []
    blocks = []
    current = None

    while index < len(raw_lines):
        raw = raw_lines[index]
        line_no = index + 1
        if LEADING_TAB_RE.match(raw):
            raise DslError("tab character in indentation", code="E_DSL_TAB",
                           filename=filename, line=line_no, text=raw,
                           hint="indent with spaces only")
        line = strip_comment(raw)
        if not line.strip():
            index += 1
            continue

        indent = indent_of(line)
        body = line.strip()

        if indent == 0:
            current = None
            block_match = BLOCK_RE.match(body)
            field_match = FIELD_RE.match(body)
            if block_match and not field_match:
                current = Block(block_match.group(1), block_match.group(2), line_no)
                blocks.append(current)
                index += 1
                continue
            if field_match:
                value, index = read_value(raw_lines, index, indent, field_match.group(2),
                                          filename)
                top_fields.append((field_match.group(1), value, line_no))
                continue
            raise DslError("expected a block header or a 'key: value' line",
                           filename=filename, line=line_no, text=raw,
                           hint="blocks look like 'node N1' or 'exports N3'")

        if current is None:
            raise DslError("indented line outside any block", filename=filename,
                           line=line_no, text=raw,
                           hint="add a 'node <id>' header above it")

        field_match = FIELD_RE.match(body) or ASSIGN_RE.match(body)
        if not field_match:
            raise DslError("expected 'field: value' or 'field = value'", filename=filename,
                           line=line_no, text=raw,
                           hint="node fields are goal, tool, in, out, after, run, "
                                "timeout, from, note; exports use 'field = $ref'")
        value, index = read_value(raw_lines, index, indent, field_match.group(2), filename)
        current.fields.append((field_match.group(1), value, line_no))

    return Document(format_version, header, top_fields, blocks, filename)


def read_value(raw_lines, index, indent, first_value, filename):
    line_no = index + 1
    if first_value.strip() == HEREDOC_OPEN:
        body, index = read_heredoc(raw_lines, index + 1, filename, line_no)
        return body, index

    parts = [first_value.strip()]
    index += 1
    while index < len(raw_lines):
        raw = raw_lines[index]
        if not raw.strip():
            break
        if indent_of(raw) <= indent:
            break
        stripped = strip_comment(raw).strip()
        if stripped:
            parts.append(stripped)
        index += 1
    return " ".join(p for p in parts if p), index


def read_heredoc(raw_lines, index, filename, open_line):
    body = []
    while index < len(raw_lines):
        if raw_lines[index].strip() == HEREDOC_CLOSE:
            dedent = min([indent_of(l) for l in body if l.strip()] or [0])
            return "\n".join(l[dedent:] if l.strip() else "" for l in body), index + 1
        body.append(raw_lines[index])
        index += 1
    raise DslError("unterminated %s block" % HEREDOC_OPEN, code="E_DSL_UNTERMINATED",
                   filename=filename, line=open_line,
                   hint="close it with a line containing only %s" % HEREDOC_CLOSE)


def unquote_header(value):
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return unescape_string(value[1:-1])
    return value


def unescape_string(raw):
    out = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "\\" and index + 1 < len(raw):
            nxt = raw[index + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def split_top_level(text, separator=","):
    parts = []
    current = []
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if char == "\\" and index + 1 < len(text):
                current.append(char)
                current.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            current.append(char)
        elif char == '"':
            in_string = True
            current.append(char)
        elif char == separator:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail or parts:
        parts.append(tail)
    return [p for p in parts if p]


def parse_ref(text, filename, line):
    inner = text[1:]
    if "." not in inner:
        raise DslError("reference %r needs a field, e.g. $N1.forecast" % text,
                       code="E_DSL_BAD_REF", filename=filename, line=line)
    target, field = inner.rsplit(".", 1)
    if not NAME_RE.match(field):
        raise DslError("bad field name in reference %r" % text, code="E_DSL_BAD_REF",
                       filename=filename, line=line)
    if target not in SPECIAL_TARGETS and not is_node_id(target):
        raise DslError("reference %r targets %r, which is not a node id or %s"
                       % (text, target, " or ".join("$" + s for s in SPECIAL_TARGETS)),
                       code="E_DSL_BAD_REF", filename=filename, line=line,
                       hint="node ids look like N1 or N3.2")
    return Ref(target, field)


def parse_value(text, filename, line):
    if not text:
        raise DslError("empty value", filename=filename, line=line)
    if text.startswith('"'):
        if len(text) < 2 or not text.endswith('"') or is_unterminated(text):
            raise DslError("unterminated string %s" % text, code="E_DSL_UNTERMINATED",
                           filename=filename, line=line)
        return Lit(unescape_string(text[1:-1]), "str")
    if text.startswith("$"):
        return parse_ref(text, filename, line)
    if NUM_RE.match(text):
        return Lit(text, "num")
    if BARE_RE.match(text):
        return Lit(text, "bare")
    raise DslError("cannot parse value %r" % text, filename=filename, line=line,
                   hint='quote it: "%s"' % text.replace('"', ''))


def is_unterminated(text):
    index = 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == '"':
            return index != len(text) - 1
        index += 1
    return True


def parse_bindings(text, filename, line):
    bindings = []
    seen = set()
    for chunk in split_top_level(text):
        if "=" not in chunk:
            raise DslError("binding %r must look like name = value" % chunk,
                           filename=filename, line=line)
        name, value = chunk.split("=", 1)
        name = name.strip()
        if not NAME_RE.match(name):
            raise DslError("bad binding name %r" % name, filename=filename, line=line)
        if name in seen:
            raise DslError("duplicate binding %r" % name, code="E_DSL_DUP_FIELD",
                           filename=filename, line=line)
        seen.add(name)
        bindings.append(Binding(name, parse_value(value.strip(), filename, line)))
    return bindings


def parse_name_list(text, filename, line, validator=None, what="name"):
    names = []
    for chunk in split_top_level(text):
        if validator is not None and not validator(chunk):
            raise DslError("bad %s %r" % (what, chunk), code="E_DSL_BAD_ID",
                           filename=filename, line=line)
        if chunk in names:
            raise DslError("duplicate %s %r" % (what, chunk), code="E_DSL_DUP_FIELD",
                           filename=filename, line=line)
        names.append(chunk)
    return names


def parse_graph(text, filename="<string>"):
    doc = parse_document(text, filename, require_header=True)
    graph = Graph(format_version=doc.format_version)
    graph.rev = doc.header.get("rev")
    graph.parent = doc.header.get("parent")
    graph.refined = doc.header.get("refined")
    graph.kind = doc.header.get("kind")
    graph.created = doc.header.get("created")
    graph.note = doc.header.get("note")
    graph.task = doc.top("task")

    for field_name, _value, line in doc.top_fields:
        if field_name != "task":
            raise DslError("unknown top-level field %r" % field_name,
                           code="E_DSL_UNKNOWN_FIELD", filename=filename, line=line,
                           hint="only 'task:' may sit outside a block")

    for block in doc.blocks:
        if block.kind == "node":
            add_node(graph, block, filename)
        elif block.kind == "exports":
            add_exports(graph, block, filename)
        else:
            raise DslError("unknown block kind %r" % block.kind, filename=filename,
                           line=block.line, hint="graphs contain 'node' and 'exports' blocks")
    return graph


def add_node(graph, block, filename):
    if not is_node_id(block.name):
        raise DslError("bad node id %r" % block.name, code="E_DSL_BAD_ID",
                       filename=filename, line=block.line,
                       hint="node ids look like N1, N3.2, N3.2.1")
    if block.name in graph.nodes:
        raise DslError("duplicate node %s" % block.name, code="E_DSL_DUP_NODE",
                       filename=filename, line=block.line)

    fields = block.field_map(filename)
    for name in fields:
        if name not in NODE_FIELDS:
            raise DslError("unknown node field %r" % name, code="E_DSL_UNKNOWN_FIELD",
                           filename=filename, line=fields[name][1],
                           hint="known fields: " + ", ".join(NODE_FIELDS))

    node = Node(block.name, line=block.line)
    if "goal" in fields:
        node.goal = fields["goal"][0]
    if "tool" in fields:
        value, line = fields["tool"]
        if not TOOL_NAME_RE.match(value):
            raise DslError("bad tool name %r" % value, filename=filename, line=line)
        node.tool = value
    if "in" in fields:
        node.ins = parse_bindings(fields["in"][0], filename, fields["in"][1])
    if "out" in fields:
        node.outs = parse_name_list(fields["out"][0], filename, fields["out"][1],
                                    validator=NAME_RE.match, what="output field")
    if "after" in fields:
        node.after = parse_name_list(fields["after"][0], filename, fields["after"][1],
                                     validator=is_node_id, what="node id")
    if "run" in fields:
        node.run = fields["run"][0]
    if "timeout" in fields:
        value, line = fields["timeout"]
        if not value.isdigit():
            raise DslError("timeout must be a whole number of seconds, got %r" % value,
                           filename=filename, line=line)
        node.timeout = int(value)
    if "from" in fields:
        value, line = fields["from"]
        if not is_node_id(value):
            raise DslError("bad node id %r in from:" % value, code="E_DSL_BAD_ID",
                           filename=filename, line=line)
        node.origin = value
    if "note" in fields:
        node.note = fields["note"][0]
    graph.nodes[node.id] = node


def add_exports(graph, block, filename):
    if not is_node_id(block.name):
        raise DslError("bad node id %r in exports block" % block.name,
                       code="E_DSL_BAD_ID", filename=filename, line=block.line)
    if block.name in graph.exports:
        raise DslError("duplicate exports block for %s" % block.name,
                       code="E_DSL_DUP_NODE", filename=filename, line=block.line)
    mapping = {}
    for name, value, line in block.fields:
        if name in mapping:
            raise DslError("duplicate export field %r" % name, code="E_DSL_DUP_FIELD",
                           filename=filename, line=line)
        if not value.startswith("$"):
            raise DslError("export %r must map to a $ref, got %r" % (name, value),
                           code="E_DSL_BAD_REF", filename=filename, line=line,
                           hint="write: %s = $N3.2.%s" % (name, name))
        mapping[name] = parse_ref(value, filename, line)
    graph.exports[block.name] = Exports(block.name, mapping, block.line)


def label(name):
    text = name + ":"
    return text.ljust(max(LABEL_WIDTH, len(text) + 1))


def wrap_items(items, prefix, cont_indent, width=WRAP_WIDTH):
    if not items:
        return []
    lines = []
    current = prefix + items[0] + ("," if len(items) > 1 else "")
    for index in range(1, len(items)):
        piece = items[index] + ("," if index < len(items) - 1 else "")
        candidate = current + " " + piece
        if len(candidate) > width:
            lines.append(current)
            current = " " * cont_indent + piece
        else:
            current = candidate
    lines.append(current)
    return lines


def field_lines(name, value):
    prefix = " " * BLOCK_INDENT + label(name)
    if "\n" in value:
        body = "\n".join(" " * (BLOCK_INDENT + 2) + l if l else "" for l in value.split("\n"))
        return [prefix + HEREDOC_OPEN, body, " " * BLOCK_INDENT + HEREDOC_CLOSE]
    return [prefix + value]


def node_lines(node):
    lines = ["node %s" % node.id]
    if node.goal:
        lines.extend(field_lines("goal", node.goal))
    if node.tool:
        lines.extend(field_lines("tool", node.tool))
    if node.ins:
        prefix = " " * BLOCK_INDENT + label("in")
        lines.extend(wrap_items([b.text() for b in node.ins], prefix, len(prefix)))
    if node.outs:
        prefix = " " * BLOCK_INDENT + label("out")
        lines.extend(wrap_items(node.outs, prefix, len(prefix)))
    if node.after:
        prefix = " " * BLOCK_INDENT + label("after")
        lines.extend(wrap_items(node.after, prefix, len(prefix)))
    if node.run:
        lines.extend(field_lines("run", node.run))
    if node.timeout is not None:
        lines.extend(field_lines("timeout", str(node.timeout)))
    if node.origin:
        lines.extend(field_lines("from", node.origin))
    if node.note:
        lines.extend(field_lines("note", node.note))
    return lines


def export_lines(exports):
    lines = ["exports %s" % exports.node_id]
    for field in sorted(exports.mapping):
        lines.append("%s%s = %s" % (" " * BLOCK_INDENT, field,
                                    exports.mapping[field].text()))
    return lines


def header_value(value):
    text = str(value)
    if not text or re.search(r"\s|\"", text):
        return '"%s"' % escape_string(text)
    return text


def serialize_graph(graph):
    header = ["# atg/%d" % (graph.format_version or FORMAT_VERSION)]
    for key in ("rev", "parent", "refined", "kind", "created", "note"):
        value = getattr(graph, key, None)
        if value:
            header.append("%s=%s" % (key, header_value(value)))
    lines = [" ".join(header), ""]
    if graph.task:
        lines.append("task: " + graph.task.replace("\n", " ").strip())
        lines.append("")
    for node_id in graph.display_order():
        lines.extend(node_lines(graph.nodes[node_id]))
        lines.append("")
    for node_id in sorted(graph.exports, key=id_sort_key):
        lines.extend(export_lines(graph.exports[node_id]))
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"
