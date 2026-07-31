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


import shutil
import tempfile

from . import compile as compiler
from . import repair as repairer
from .check import run_check
from .errors import BudgetError, FrozenError
from .execute import loop
from .metrics import collect
from .render import render
from .schedule import frontier_widths, ready_report
from .store import create_run, parse_budgets, resolve_run
from .tools import parse_registry

TOOLS = os.path.join(FIXTURES, "selftest_tools.atg")

R0 = """node 1
  goal: fetch raw data
  tool: shell
  in:   cmd = "echo 42"
  out:  raw
  run:  echo 42

node 2
  goal: turn raw data into the answer
  in:   raw = $N1.raw
  out:  answer

exports N0
  answer = $N2.answer
"""

R2_BAD = """node 1
  goal: clean it
  tool: shell
  in:   raw = $N1.raw
  out:  clean
  run:  echo clean

node 2
  goal: phrase it
  tool: shell
  in:   clean = $1.clean
  out:  answer
  run:  exit 3

exports N2
  answer = $N2.2.answer
"""

R2_FIX = R2_BAD.replace("run:  exit 3", 'run:  echo "answer is $N2.1.clean"').replace(
    "out:  clean\n  run:  echo clean", "out:  clean\n  from: N2.1\n  run:  echo clean")


class sandbox(object):
    def __init__(self, task="report the weather", tools=True):
        self.task = task
        self.tools = tools

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="atg-selftest-")
        self.run = create_run(self.task, outputs=["answer"],
                              tools_path=TOOLS if self.tools else None,
                              root=self.dir)
        return self.run

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)


def compiled_run(box):
    compiler.refine(box, ROOT_ID, R0)
    compiler.refine(box, "N2", R2_BAD)
    return box


@case
def t_registry_parses_template():
    with open(TOOLS, "r") as handle:
        registry = parse_registry(handle.read(), TOOLS)
    assert "shell" in registry.tools
    assert [p.name for p in registry.tools["shell"].ins] == ["cmd", "raw", "clean"]


@case
def t_budget_parsing():
    assert parse_budgets(["max_depth=3"]) == {"max_depth": 3}
    for bad in (["nope=1"], ["max_depth"], ["max_depth=x"], ["max_depth=0"]):
        try:
            parse_budgets(bad)
        except AtgError:
            continue
        raise AssertionError("accepted bad budget %r" % bad)


@case
def t_run_creation_and_resolution():
    with sandbox() as box:
        assert box.head() == "G000"
        assert box.read_revision().nodes[ROOT_ID].outs == ["answer"]
        assert resolve_run(root=os.path.dirname(box.path)).id == box.id
        first = box.append_event("probe")["seq"]
        assert box.append_event("probe")["seq"] == first + 1


@case
def t_refine_normalizes_local_ids():
    with sandbox() as box:
        out = compiler.refine(box, ROOT_ID, R0)
        assert out["added"] == ["N1", "N2"]
        graph = box.read_revision()
        assert graph.rev == "G001" and graph.refined == ROOT_ID
        assert graph.nodes["N2"].binding("raw").value.text() == "$N1.raw"
        out = compiler.refine(box, "N2", R2_BAD)
        assert out["added"] == ["N2.1", "N2.2"]
        graph = box.read_revision()
        assert graph.nodes["N2.2"].binding("clean").value.text() == "$N2.1.clean"
        assert graph.resolve_ref(Ref("N2", "answer")) == ("N2.2", "answer")


@case
def t_interface_violations():
    cases = [
        ("node 1\n  tool: shell\n  in: x = $N2.answer\n  out: answer\n  run: true\n"
         "\nexports N2\n  answer = $N2.1.answer\n", "E_IFACE_SELF"),
        ("node 1\n  tool: shell\n  in: x = $N9.nope\n  out: answer\n  run: true\n"
         "\nexports N2\n  answer = $N2.1.answer\n", "E_IFACE_INPUT"),
        ("node 1\n  tool: shell\n  in: raw = $N1.raw\n  out: other\n  run: true\n",
         "E_IFACE_OUTPUT"),
        ("node N7\n  tool: shell\n  in: raw = $N1.raw\n  out: answer\n  run: true\n"
         "\nexports N2\n  answer = $N7.answer\n", "E_IFACE_SCOPE"),
    ]
    for text, code in cases:
        with sandbox() as box:
            compiler.refine(box, ROOT_ID, R0)
            try:
                compiler.refine(box, "N2", text)
            except AtgError as err:
                codes = [i.code for i in (err.issues or [])] + [err.code]
                assert code in codes, "expected %s, got %s" % (code, codes)
            else:
                raise AssertionError("%s was accepted" % code)


@case
def t_interface_warnings():
    with sandbox() as box:
        compiler.refine(box, ROOT_ID, R0)
        text = ("node 1\n  tool: shell\n  in: raw = $N1.raw\n  out: answer\n  run: true\n"
                "\nnode 2\n  tool: shell\n  in: raw = $N1.raw\n  out: spare\n  run: true\n"
                "\nexports N2\n  answer = $1.answer\n  extra = $N2.2.spare\n")
        out = compiler.refine(box, "N2", text)
        codes = set(i["class"] for i in out["issues"])
        assert "W_IFACE_WIDE" in codes, codes


@case
def t_budget_refusal():
    with sandbox() as box:
        box.save_meta(dict(box.meta(), budgets={"max_fanout": 1}))
        try:
            compiler.refine(box, ROOT_ID, R0)
        except BudgetError:
            return
        raise AssertionError("fanout budget not enforced")


@case
def t_scheduler_frontiers():
    with sandbox() as box:
        compiled_run(box)
        graph = box.read_revision()
        report = ready_report(box, graph)
        assert [n["id"] for n in report["nodes"]] == ["N1"]
        assert report["frontier"] == 0
        assert [w["id"] for w in report["waiting"]] == ["N2.1", "N2.2"]


@case
def t_check_clean_and_dirty():
    with sandbox() as box:
        compiled_run(box)
        clean = run_check(box)
        assert clean["exit"] == 0, clean["issues"]
        broken = box.read_revision()
        broken.nodes["N2.1"].tool = "no_such_tool"
        box.write_revision(broken)
        result = run_check(box)
        assert result["exit"] != 0
        assert "X_TOOL" in [i.code for i in result["issues"]], result["issues"]


@case
def t_execute_repair_reuse_and_freeze():
    with sandbox() as box:
        compiled_run(box)
        loop(box)
        states = box.node_states()
        assert states["N1"].status == "done" and states["N2.2"].status == "failed"

        blamed = repairer.blame(box)
        assert blamed["failed"] == ["N2.2"]
        assert blamed["lca"] == "N2" and blamed["frozen"] == ["N1"]
        assert blamed["boundary_inputs"]["$N1.raw"] == "42"
        assert blamed["reusable_outputs"]["N2.1.clean"] == "clean"

        data = compiler.context(box, "N2", repair=True)
        assert data["node"]["out"] == ["answer"]
        assert data["node"]["in"] == ["raw = $N1.raw"]

        try:
            compiler.refine(box, "N2", R2_FIX, allow_atomic=True, frozen=set(["N2.1"]))
        except FrozenError:
            pass
        else:
            raise AssertionError("a frozen node was rewritten")

        out = repairer.repair(box, "N2", R2_FIX)
        assert out["reused"] == ["N2.1"], out["reused"]
        assert out["frozen"] == ["N1"]
        loop(box)
        states = box.node_states()
        assert set(s.status for s in states.values()) == set(["done"])

        data = collect(box)
        assert data["repairs"] == 1 and data["reused_outputs"] == 1
        assert data["failure_precision"] == "n/a"
        assert data["frozen_not_rerun"] == 1
        assert data["steps"] == 3


@case
def t_lca_prefix_vs_history():
    assert repairer.prefix_ancestor(["N3.2"]) == "N3"
    assert repairer.prefix_ancestor(["N3.1", "N3.2"]) == "N3"
    assert repairer.prefix_ancestor(["N1", "N3.2"]) == ROOT_ID


@case
def t_render_formats():
    with sandbox() as box:
        compiled_run(box)
        graph = box.read_revision()
        states = box.node_states(graph)
        mermaid = render(graph, states, "mermaid", status=True)
        assert mermaid.startswith("flowchart") and "N2.1" in mermaid
        assert "digraph" in render(graph, states, "dot")
        assert "rank 0" in render(graph, states, "ascii")
        assert "| node |" in render(graph, states, "md").lower()


@case
def t_refined_away_ancestor_has_an_interface():
    with sandbox() as box:
        compiled_run(box)
        graph = box.read_revision()
        assert "N2" not in graph.nodes
        node = compiler.live_node(graph, "N2")
        assert node.outs == ["answer"]
        assert [b.value.text() for b in node.ins] == ["$N1.raw"]
        assert compiler.live_node(graph, "N9") is None


WEATHER_TOOLS = os.path.join(FIXTURES, "weather_tools.atg")

FIG3_ROOT = """node 1
  goal: fetch tomorrow's forecast for the city
  tool: weather_api
  in:   city = $task.city, date = $task.date
  out:  forecast
  run:  echo '{"forecast": "rain 3mm"}'

node 2
  goal: confirm the city name resolves to exactly one place
  tool: geocode
  in:   q = $task.city
  out:  place_id
  run:  echo beijing-1

node 3
  goal: turn the forecast into travel advice
  in:   src = $N1.forecast, place = $N2.place_id
  out:  advice

node 4
  goal: write the final travel advice for the user
  tool: compose
  in:   advice = $N3.advice, forecast = $N1.forecast
  out:  answer
  run:  echo "take an umbrella: $N3.advice"

exports N0
  answer = $N4.answer
"""

FIG3_N3 = """node 1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast
  out:  temp_c
  run:  echo 14

node 2
  goal: name the place the forecast is for
  tool: label
  in:   place = $N2.place_id
  out:  place_name
  run:  echo beijing

node 3
  goal: decide umbrella and clothing from the extracted conditions
  tool: llm_judge
  in:   t = $1.temp_c, p = $2.place_name
  out:  advice
  run:  exit 1

exports N3
  advice = $3.advice
"""

FIG3_FIX = FIG3_N3.replace("run:  echo 14", "from: N3.1\n  run:  echo 14").replace(
    "run:  echo beijing\n", "from: N3.2\n  run:  echo beijing\n").replace(
    "run:  exit 1", 'run:  echo "umbrella in $N3.2.place_name at $N3.1.temp_c C"')


@case
def t_end_to_end_figure_3():
    with sandbox(task="check tomorrow's weather in beijing, give travel advice",
                 tools=False) as box:
        shutil.copyfile(WEATHER_TOOLS, box.tools_path)
        box.save_meta(dict(box.meta(), inputs={"city": "beijing", "date": "tomorrow"}))

        compiler.refine(box, ROOT_ID, FIG3_ROOT)
        assert box.read_revision().open_nodes() == ["N3"]
        compiler.refine(box, "N3", FIG3_N3)
        graph = box.read_revision()
        assert graph.open_nodes() == []
        assert graph.node_ids() == ["N1", "N2", "N3.1", "N3.2", "N3.3", "N4"]
        assert graph.resolve_ref(Ref("N3", "advice")) == ("N3.3", "advice")

        clean = run_check(box)
        assert clean["exit"] == 0, [i.message for i in clean["issues"]]
        assert [r for r in box.events(("check_pass",))][-1]["phase"] == "pre_exec"

        result = loop(box)
        assert result["status"] == "blocked"
        states = box.node_states()
        assert [states[i].status for i in ("N1", "N2", "N3.1", "N3.2")] == ["done"] * 4
        assert states["N3.3"].status == "failed" and states["N4"].status == "pending"
        assert [s["frontier"] for s in result["steps"]] == [0, 1, 2]

        blamed = repairer.blame(box)
        assert blamed["failed"] == ["N3.3"]
        assert blamed["lca"] == "N3", blamed
        assert blamed["lca_by_prefix"] == blamed["lca_by_history"]
        assert blamed["scope"] == ["N3.1", "N3.2", "N3.3"]
        assert blamed["frozen"] == ["N1", "N2", "N4"]
        assert blamed["boundary_inputs"] == {"$N1.forecast": "rain 3mm",
                                             "$N2.place_id": "beijing-1"}
        assert sorted(blamed["reusable_outputs"]) == ["N3.1.temp_c", "N3.2.place_name"]

        before = dict((i, box.read_revision().nodes[i]) for i in ("N1", "N2", "N4"))
        out = repairer.repair(box, "N3", FIG3_FIX)
        assert out["reused"] == ["N3.1", "N3.2"], out["reused"]
        assert out["frozen"] == ["N1", "N2", "N4"]
        after = box.read_revision()
        for node_id, node in before.items():
            assert serialize_node(after.nodes[node_id]) == serialize_node(node)

        result = loop(box)
        assert result["status"] == "done", result
        assert result["outputs"]["answer"].startswith("take an umbrella: umbrella in beijing")
        states = box.node_states()
        assert set(s.status for s in states.values()) == set(["done"])

        data = collect(box)
        assert data["steps"] == 4 and data["frontier_widths"] == [2, 2, 1, 1]
        assert data["serial_steps"] == 6
        assert data["repairs"] == 1 and data["repair_success_rate"] == 1.0
        assert data["reused_outputs"] == 2
        assert data["saved_environment_interactions"] >= 2
        assert data["failure_precision"] == "n/a"
        assert data["hallucinatory_trajectory"] is True


def serialize_node(node):
    return (node.id, node.goal, node.tool, [b.text() for b in node.ins], list(node.outs),
            node.run)


@case
def t_frozen_downstream_still_runs():
    with sandbox(task="repair must not deadlock the nodes it froze", tools=False) as box:
        shutil.copyfile(WEATHER_TOOLS, box.tools_path)
        box.save_meta(dict(box.meta(), inputs={"city": "beijing", "date": "tomorrow"}))
        compiler.refine(box, ROOT_ID, FIG3_ROOT)
        compiler.refine(box, "N3", FIG3_N3)
        loop(box)
        repairer.repair(box, "N3", FIG3_FIX)
        states = box.node_states()
        assert states["N4"].frozen is True and states["N4"].status == "pending"
        assert states["N1"].frozen is True and states["N1"].status == "done"
        assert [n["id"] for n in ready_report(box)["nodes"]] == ["N3.3"]
        assert loop(box)["status"] == "done"
        assert box.node_states()["N4"].status == "done"


SHAPE_HEAD = """node 1
  tool: shell
  in:   cmd = "a"
  out:  a
"""


def shape(body, answer):
    return SHAPE_HEAD + body + "\nexports N0\n  answer = $%s.answer\n" % answer


CHAIN = shape("""
node 2
  tool: shell
  in:   raw = $1.a
  out:  b

node 3
  tool: shell
  in:   raw = $2.b
  out:  answer
""", "N3")

DIAMOND = shape("""
node 2
  tool: shell
  in:   raw = $1.a
  out:  b

node 3
  tool: shell
  in:   raw = $1.a
  out:  c

node 4
  tool: shell
  in:   raw = $2.b, clean = $3.c
  out:  answer
""", "N4")

FANOUT = shape("""
node 2
  tool: shell
  in:   raw = $1.a
  out:  b

node 3
  tool: shell
  in:   raw = $1.a
  out:  c

node 4
  tool: shell
  in:   raw = $1.a
  out:  d

node 5
  tool: shell
  in:   raw = $2.b, clean = $3.c
  out:  answer
""", "N5")

AFTER_ONLY = shape("""
node 2
  tool: shell
  in:   cmd = "b"
  out:  answer
  after: N1
""", "N2")

CYCLIC = """node 1
  tool: shell
  in:   raw = $2.b
  out:  a

node 2
  tool: shell
  in:   raw = $1.a
  out:  answer

exports N0
  answer = $N2.answer
"""


def drain(box, graph):
    states = box.node_states(graph)
    widths = []
    while True:
        report = ready_report(box, graph, states)
        if not report["nodes"]:
            return widths
        widths.append(len(report["nodes"]))
        for entry in report["nodes"]:
            box.append_event("done", node=entry["id"], frontier=report["frontier"],
                             out=dict((f, "v") for f in entry["out"]))
        states = box.node_states(graph)


@case
def t_scheduler_shapes():
    for name, text, expected in (("chain", CHAIN, [1, 1, 1]),
                                 ("diamond", DIAMOND, [1, 2, 1]),
                                 ("fanout", FANOUT, [1, 3, 1]),
                                 ("after_only", AFTER_ONLY, [1, 1])):
        with sandbox() as box:
            compiler.refine(box, ROOT_ID, text)
            graph = box.read_revision()
            assert drain(box, graph) == expected, name
            assert frontier_widths(graph, box.node_states(graph)) == expected, name


@case
def t_after_edge_blocks_until_done():
    with sandbox() as box:
        compiler.refine(box, ROOT_ID, AFTER_ONLY)
        graph = box.read_revision()
        report = ready_report(box, graph)
        assert [n["id"] for n in report["nodes"]] == ["N1"]
        assert report["waiting"][0]["why"] == ["after N1 is pending"]


@case
def t_cycle_is_refused():
    with sandbox() as box:
        try:
            compiler.refine(box, ROOT_ID, CYCLIC)
        except AtgError as err:
            assert err.code == "E_CYCLE", err.code
        else:
            raise AssertionError("a cyclic subgraph was accepted")


@case
def t_lca_history_beats_prefix():
    parents = {"N3.1": "N3", "N3.2": "N3", "N3": ROOT_ID, "N7": ROOT_ID}
    origins = {"N7": "N3.2"}
    chain = repairer.history_chain("N7", parents, origins)
    assert chain == [ROOT_ID, "N3", "N3.2", "N7"], chain
    assert repairer.prefix_ancestor(["N7"]) == ROOT_ID


@case
def t_metrics_from_canned_events():
    with sandbox() as box:
        compiled_run(box)
        for node_id, fields in (("N1", {"raw": "42"}), ("N2.1", {"clean": "clean"})):
            box.append_event("done", node=node_id, out=fields, ms=5)
        box.append_event("fail", node="N2.2", err="exit 3", ms=1, **{"class": "X_TOOL"})
        data = collect(box)
        assert data["steps"] == 2 and data["frontier_widths"] == [1, 1]
        assert data["executions"] == 3 and data["failures"] == 1
        assert data["hallucinatory_action_rate"] == round(1.0 / 3, 4)
        assert data["failure_precision"] == "n/a"
        assert data["repairs"] == 0 and data["repair_success_rate"] is None
        assert data["saved_environment_interactions"] == 0


@case
def t_render_golden():
    with sandbox() as box:
        compiler.refine(box, ROOT_ID, R0)
        graph = box.read_revision()
        states = box.node_states(graph)
        assert render(graph, states, "mermaid").splitlines()[:4] == [
            "flowchart TD",
            '  N1["N1<br/>fetch raw data<br/>[shell]"]',
            '  N2("N2<br/>turn raw data into the answer")',
            "  N1 -->|raw| N2",
        ]
        assert render(graph, states, "dot").splitlines()[0] == "digraph atg {"
        ascii_art = render(graph, states, "ascii")
        assert "rank 0" in ascii_art and "N1" in ascii_art and "│" in ascii_art


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
