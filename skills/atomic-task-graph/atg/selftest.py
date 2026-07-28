import os
import random
import sys

from .dsl import parse_document, parse_graph, serialize_graph
from .errors import AtgError, DslError
from .model import (ROOT_ID, Graph, Lit, Node, Ref, Binding, common_ancestor, id_child,
                    id_depth, id_parent, id_sort_key, is_descendant, is_node_id)

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures")
CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def fixture(name):
    with open(os.path.join(FIXTURES, name), "r") as handle:
        return handle.read()


def expect_dsl_error(text, code, what):
    try:
        parse_graph(text, "<case>")
    except DslError as err:
        assert err.code == code, "%s: expected %s, got %s (%s)" % (what, code, err.code,
                                                                   err.message)
        return
    raise AssertionError("%s: expected %s, parsed clean" % (what, code))


@case
def t_id_helpers():
    assert is_node_id("N1") and is_node_id("N3.2") and is_node_id("N12.3.4")
    assert not is_node_id("n1") and not is_node_id("N") and not is_node_id("N1.")
    assert id_sort_key("N3.10") > id_sort_key("N3.2")
    assert sorted(["N10", "N2", "N1.5"], key=id_sort_key) == ["N1.5", "N2", "N10"]
    assert id_depth(ROOT_ID) == 0 and id_depth("N1") == 1 and id_depth("N3.2.1") == 3
    assert id_child(ROOT_ID, 3) == "N3"
    assert id_child("N3", 2) == "N3.2"
    assert id_parent("N3.2.1") == "N3.2"
    assert id_parent("N3") == ROOT_ID
    assert id_parent(ROOT_ID) is None
    assert is_descendant("N3.2", "N3") and not is_descendant("N30", "N3")
    assert is_descendant("N3", ROOT_ID) and not is_descendant(ROOT_ID, ROOT_ID)


@case
def t_common_ancestor():
    assert common_ancestor(["N3.1", "N3.2"]) == "N3"
    assert common_ancestor(["N3.2.1", "N3.2.7"]) == "N3.2"
    assert common_ancestor(["N3.2"]) == "N3.2"
    assert common_ancestor(["N1", "N3.2"]) == ROOT_ID
    assert common_ancestor([]) == ROOT_ID
    assert common_ancestor([ROOT_ID]) == ROOT_ID
    assert common_ancestor(["N3.1", "N3.1.4"]) == "N3.1"


@case
def t_parse_weather_fixture():
    graph = parse_graph(fixture("weather_g003.atg"), "weather_g003.atg")
    assert graph.rev == "G003" and graph.parent == "G002" and graph.refined == "N3"
    assert graph.task.startswith("check tomorrow's weather")
    assert graph.node_ids() == ["N1", "N2", "N3.1", "N3.2", "N4"]
    assert graph.open_nodes() == []
    node = graph.nodes["N1"]
    assert node.tool == "weather_api" and node.outs == ["forecast"]
    assert node.binding("city").value == Lit("beijing", "str")
    assert node.binding("date").value == Ref("task", "date")


@case
def t_export_resolution_makes_the_edge():
    graph = parse_graph(fixture("weather_g003.atg"), "weather_g003.atg")
    assert graph.resolve_ref(Ref("N3", "advice")) == ("N3.2", "advice")
    assert graph.resolve_ref(Ref("task", "date")) is None
    assert graph.resolve_ref(Ref("N9", "nope")) is None
    edges = set((s, d) for s, d, _f, _k in graph.edges())
    assert ("N3.2", "N4") in edges, "ref to a refined-away node must edge to its exporter"
    assert ("N1", "N4") in edges and ("N1", "N3.1") in edges and ("N2", "N3.1") in edges
    assert ("N3.1", "N3.2") in edges


@case
def t_topology():
    graph = parse_graph(fixture("weather_g003.atg"), "weather_g003.atg")
    order = graph.topo_order()
    assert order.index("N1") < order.index("N3.1") < order.index("N3.2") < order.index("N4")
    rank = graph.topo_rank()
    assert rank["N1"] == 0 and rank["N2"] == 0
    assert rank["N3.1"] == 1 and rank["N3.2"] == 2 and rank["N4"] == 3
    assert graph.preds("N3.1") == ["N1", "N2"]
    assert graph.succs("N1") == ["N3.1", "N4"]


@case
def t_after_edges_and_heredoc():
    graph = parse_graph(fixture("embodied_g002.atg"), "embodied_g002.atg")
    assert graph.kind == "repair"
    assert graph.note == "second attempt at the fridge"
    edges = set((s, d, k) for s, d, _f, k in graph.edges())
    assert ("N1", "N2.1", "after") in edges, "after: must produce a control edge"
    assert ("N2.1", "N2.2", "data") in edges
    assert ("N2.2", "N3", "data") in edges, "$N2.held must resolve through exports N2"
    node = graph.nodes["N3"]
    assert node.timeout == 45
    assert node.run == 'echo "put egg on countertop"\nexit 0'
    assert graph.nodes["N2.2"].origin == "N2"
    assert graph.nodes["N2.2"].note.startswith("previous attempt failed")


@case
def t_cycle_detection_names_the_nodes():
    text = ("# atg/1 rev=G000\n\nnode N1\n  tool: a\n  in:   x = $N2.y\n  out:  y\n\n"
            "node N2\n  tool: b\n  in:   x = $N1.y\n  out:  y\n")
    graph = parse_graph(text, "<cycle>")
    try:
        graph.topo_order()
    except AtgError as err:
        assert err.code == "E_CYCLE"
        assert set(err.nodes) == set(["N1", "N2"])
        return
    raise AssertionError("cycle went undetected")


@case
def t_non_atomic_nodes_are_the_worklist():
    text = ("# atg/1 rev=G000\n\ntask: t\n\nnode N1\n  goal: still coarse\n  out:  answer\n")
    graph = parse_graph(text, "<open>")
    assert graph.open_nodes() == ["N1"]
    assert not graph.nodes["N1"].is_atomic


@case
def t_round_trip_is_a_fixed_point():
    for name in ("weather_g003.atg", "embodied_g002.atg"):
        once = serialize_graph(parse_graph(fixture(name), name))
        twice = serialize_graph(parse_graph(once, name))
        assert once == twice, "%s: serialize is not idempotent\n---\n%s\n---\n%s" % (
            name, once, twice)


@case
def t_serialized_layout():
    graph = parse_graph(fixture("weather_g003.atg"), "weather_g003.atg")
    lines = serialize_graph(graph).splitlines()
    assert lines[0] == "# atg/1 rev=G003 parent=G002 refined=N3"
    assert "  goal: fetch tomorrow's forecast for beijing" in lines
    assert "  in:   city = \"beijing\", date = $task.date" in lines
    assert "  out:  forecast" in lines
    assert "exports N3" in lines
    assert "  advice = $N3.2.advice" in lines
    for line in lines:
        assert len(line) <= 88 or "goal:" in line or "note:" in line, "unwrapped: %r" % line


@case
def t_long_binding_list_wraps_and_reparses():
    ins = [Binding("k%02d" % i, Lit("value-%02d" % i, "str")) for i in range(12)]
    graph = Graph(rev="G000", task="t",
                  nodes={"N1": Node("N1", goal="wide", tool="t", ins=ins, outs=["o"])})
    text = serialize_graph(graph)
    body = [l for l in text.splitlines() if l.startswith("  ")]
    assert len(body) > 4, "a 12-binding list should wrap"
    again = parse_graph(text, "<wrap>")
    assert [b.name for b in again.nodes["N1"].ins] == [b.name for b in ins]
    assert serialize_graph(again) == text


@case
def t_fuzz_round_trip():
    rng = random.Random(20260728)
    tools = ["search", "read_file", "compute", "compose", "judge"]
    for trial in range(60):
        count = rng.randint(1, 9)
        nodes = {}
        ids = []
        for index in range(1, count + 1):
            if ids and rng.random() < 0.45:
                node_id = id_child(rng.choice(ids), rng.randint(1, 4))
                if node_id in nodes:
                    node_id = id_child(ROOT_ID, index + 100)
            else:
                node_id = id_child(ROOT_ID, index)
            ins = []
            for prior in ids:
                if nodes[prior].outs and rng.random() < 0.4:
                    ins.append(Binding("a%s" % len(ins),
                                       Ref(prior, nodes[prior].outs[0])))
            if rng.random() < 0.5:
                ins.append(Binding("lit%d" % len(ins),
                                   Lit("v %d, with comma" % index, "str")))
            if rng.random() < 0.3:
                ins.append(Binding("num%d" % len(ins), Lit(str(rng.randint(0, 999)), "num")))
            node = Node(node_id, goal="goal %d" % index, tool=rng.choice(tools), ins=ins,
                        outs=["o%d" % index])
            if ids and rng.random() < 0.25:
                node.after = [rng.choice(ids)]
            if rng.random() < 0.15:
                node.run = "echo %d\necho done" % index
            nodes[node_id] = node
            ids.append(node_id)
        graph = Graph(rev="G%03d" % trial, task="fuzz task %d" % trial, nodes=nodes)
        once = serialize_graph(graph)
        twice = serialize_graph(parse_graph(once, "<fuzz%d>" % trial))
        assert once == twice, "fuzz %d not idempotent\n---\n%s\n---\n%s" % (trial, once, twice)


@case
def t_dsl_errors():
    expect_dsl_error("node N1\n  tool: a\n", "E_DSL_SYNTAX", "missing header")
    expect_dsl_error("# atg/1\n\nnode N1\n\tgoal: x\n", "E_DSL_TAB", "tab indent")
    expect_dsl_error("# atg/1\n\nnode N1\n  goal: a\n\nnode N1\n  goal: b\n",
                     "E_DSL_DUP_NODE", "duplicate node")
    expect_dsl_error("# atg/1\n\nnode N1\n  goal: a\n  goal: b\n",
                     "E_DSL_DUP_FIELD", "duplicate field")
    expect_dsl_error("# atg/1\n\nnode Q1\n  goal: a\n", "E_DSL_BAD_ID", "bad node id")
    expect_dsl_error("# atg/1\n\nnode N1\n  in:   x = $nope.y\n",
                     "E_DSL_BAD_REF", "bad ref target")
    expect_dsl_error("# atg/1\n\nnode N1\n  in:   x = $N1\n", "E_DSL_BAD_REF", "ref no field")
    expect_dsl_error('# atg/1\n\nnode N1\n  in:   x = "unclosed\n',
                     "E_DSL_UNTERMINATED", "unterminated string")
    expect_dsl_error("# atg/1\n\nnode N1\n  run:  <<<\n  echo hi\n",
                     "E_DSL_UNTERMINATED", "unterminated heredoc")
    expect_dsl_error("# atg/1\n\nnode N1\n  colour: red\n",
                     "E_DSL_UNKNOWN_FIELD", "unknown node field")
    expect_dsl_error("# atg/1\n\nmood: cheerful\n", "E_DSL_UNKNOWN_FIELD", "unknown top field")
    expect_dsl_error("# atg/1\n\nexports N3\n  advice: N3.2.advice\n",
                     "E_DSL_BAD_REF", "export target must be a $ref")


@case
def t_comments_and_blank_lines():
    text = ("# atg/1 rev=G000\n"
            "# a whole-line comment\n"
            "task: t   # trailing comment\n"
            "\n"
            "node N1   # about this node\n"
            '  goal: keep the # inside a string\n'
            '  in:   x = "a # b", y = 2\n'
            "  tool: t\n"
            "  out:  o\n")
    graph = parse_graph(text, "<comments>")
    assert graph.task == "t"
    assert graph.nodes["N1"].binding("x").value == Lit("a # b", "str")
    assert graph.nodes["N1"].binding("y").value == Lit("2", "num")
    assert graph.nodes["N1"].goal == "keep the"


@case
def t_string_escapes():
    text = ('# atg/1 rev=G000\n\nnode N1\n  tool: t\n'
            '  in:   q = "say \\"hi\\"", p = "line\\nbreak", s = "back\\\\slash"\n  out:  o\n')
    graph = parse_graph(text, "<esc>")
    node = graph.nodes["N1"]
    assert node.binding("q").value.raw == 'say "hi"'
    assert node.binding("p").value.raw == "line\nbreak"
    assert node.binding("s").value.raw == "back\\slash"
    assert serialize_graph(parse_graph(serialize_graph(graph), "<esc>")) == serialize_graph(graph)


@case
def t_document_reader_handles_tool_blocks():
    text = ("tool weather_api\n"
            "  desc: forecast for a city and date\n"
            "  in:   city:str!, date:str!\n"
            "  out:  forecast:json\n")
    doc = parse_document(text, "<tools>", require_header=False)
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert block.kind == "tool" and block.name == "weather_api"
    assert dict((n, v) for n, v, _l in block.fields)["in"] == "city:str!, date:str!"


def run(verbose=False):
    failures = []
    for fn in CASES:
        name = fn.__name__[2:]
        try:
            fn()
        except Exception as err:
            failures.append((name, err))
            sys.stdout.write("FAIL %s\n  %s\n" % (name, err))
        else:
            if verbose:
                sys.stdout.write("ok   %s\n" % name)
    total = len(CASES)
    sys.stdout.write("\n%d/%d passed\n" % (total - len(failures), total))
    return 1 if failures else 0
