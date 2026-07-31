import re

from .dsl import parse_document, split_top_level
from .errors import DslError, Issue, WARNING
from .model import Param, Registry, ToolSpec

PARAM_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?::([A-Za-z_][A-Za-z0-9_\[\]]*))?(!?)$")
TOOL_FIELDS = ("desc", "in", "out")


def parse_params(text, filename, line, what):
    params = []
    seen = set()
    for chunk in split_top_level(text):
        match = PARAM_RE.match(chunk)
        if not match:
            raise DslError("cannot parse %s parameter %r" % (what, chunk),
                           filename=filename, line=line,
                           hint="write them as name, name:type, or name:type!")
        name, type_name, required = match.groups()
        if name in seen:
            raise DslError("duplicate %s parameter %r" % (what, name),
                           code="E_DSL_DUP_FIELD", filename=filename, line=line)
        seen.add(name)
        params.append(Param(name, type_name, required == "!"))
    return params


def parse_registry(text, filename="<string>"):
    doc = parse_document(text, filename, require_header=False)
    registry = Registry(source=filename)
    for field_name, _value, line in doc.top_fields:
        raise DslError("unknown top-level field %r in a tool registry" % field_name,
                       code="E_DSL_UNKNOWN_FIELD", filename=filename, line=line,
                       hint="a registry contains only 'tool <name>' blocks")
    for block in doc.blocks:
        if block.kind != "tool":
            raise DslError("unknown block kind %r in a tool registry" % block.kind,
                           filename=filename, line=block.line,
                           hint="a registry contains only 'tool <name>' blocks")
        if block.name in registry.tools:
            raise DslError("duplicate tool %r" % block.name, code="E_DSL_DUP_NODE",
                           filename=filename, line=block.line)
        fields = block.field_map(filename)
        for name in fields:
            if name not in TOOL_FIELDS:
                raise DslError("unknown tool field %r" % name, code="E_DSL_UNKNOWN_FIELD",
                               filename=filename, line=fields[name][1],
                               hint="known fields: " + ", ".join(TOOL_FIELDS))
        spec = ToolSpec(block.name, line=block.line)
        if "desc" in fields:
            spec.desc = fields["desc"][0]
        if "in" in fields:
            spec.ins = parse_params(fields["in"][0], filename, fields["in"][1], "input")
        if "out" in fields:
            spec.outs = parse_params(fields["out"][0], filename, fields["out"][1], "output")
        registry.tools[block.name] = spec
    return registry


def check_registry(registry):
    issues = []
    if registry.is_empty:
        issues.append(Issue("X_TOOL", "no tools declared", severity=WARNING,
                            hint="run `atg tools --init`, then edit it to match the tools "
                                 "you actually have"))
        return issues
    for name in registry.names():
        spec = registry.tools[name]
        if not spec.desc:
            issues.append(Issue("X_TOOL", "tool %r has no desc:" % name, severity=WARNING,
                                hint="the description is what a planning agent reads to "
                                     "choose between tools"))
        if not spec.outs:
            issues.append(Issue("X_TOOL", "tool %r declares no outputs" % name,
                                severity=WARNING,
                                hint="without out: fields, nothing downstream can $ref it"))
    return issues
