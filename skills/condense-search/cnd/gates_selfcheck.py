"""Self-check for the condense accuracy gates.

Run: python -m cnd.gates_selfcheck  (from skill root)
Or:  python cnd/gates_selfcheck.py
"""
from __future__ import annotations

from .gates import gate_quote, numbers_match_claim, run_gates
from .util import norm_quote_key


def _mk(claim: str, quote: str, **kw) -> dict:
    c = {"claim": claim, "quote": quote, "source_url": "https://a.example/x", "type": "measurement", "stance": "asserts", "numbers": [], "source_class": "peer-reviewed", "channel": "warrant"}
    c.update(kw)
    return c


def main() -> int:
    fails = 0

    # 1. number in claim must be in quote window (support fail detector)
    c = _mk("X reduces mortality 40%", "The trial reported no reduction in mortality.", numbers=[{"value": "40", "unit": "%", "stat": "RRR"}])
    ok, missing = numbers_match_claim(c, "The trial reported no reduction in mortality.")
    if ok:
        print("FAIL: number gate let 40% through with no 40% in quote"); fails += 1
    else:
        print(f"ok: number gate caught missing {missing}")

    # number present -> passes
    c2 = _mk("X reduces mortality 40%", "Mortality fell 40% in the group.", numbers=[{"value": "40", "unit": "%", "stat": "RRR"}])
    ok2, _ = numbers_match_claim(c2, "Mortality fell 40% in the group.")
    if not ok2:
        print("FAIL: number gate rejected a present number"); fails += 1
    else:
        print("ok: number gate passes when figure is in quote")

    # 2. negation polarity: causal claim from negated quote
    c3 = _mk("The drug reduces fever", "The drug showed no effect on fever.", numbers=[])
    from .gates import negation_polarity_ok
    pok, reason = negation_polarity_ok(c3, "")
    if pok:
        print("FAIL: polarity gate missed negation mismatch"); fails += 1
    else:
        print(f"ok: polarity gate caught mismatch ({reason})")

    # 3. a quote that is NOT a verbatim substring of the page is UNCHECKED
    page = "The compound demonstrated a forty one percent reduction in observed symptomatic events across the treated cohort over twelve weeks."
    q_notfound = "this exact phrase does not appear anywhere in the page corpus at all"
    claims = [
        {**_mk("Symptomatic events fell 41%", q_notfound, source_url="https://w1.example/a", source_class="peer-reviewed"), "numbers": [{"value": "41", "unit": "%"}]},
        {**_mk("Symptomatic events fell 41%", q_notfound, source_url="https://w2.example/a", source_class="peer-reviewed"), "numbers": [{"value": "41", "unit": "%"}]},
    ]
    gated, _ = run_gates(claims, {"https://w1.example/a": page, "https://w2.example/a": page})
    for g in gated:
        if g.get("status") != "UNCHECKED" or g.get("quote_found"):
            print("FAIL: non-substring quote was not rejected as UNCHECKED"); fails += 1
            break
    else:
        print("ok: non-substring quote rejected (UNCHECKED)")

    # 4. echo near-duplicate collapse: same quote across 3 domains -> 1 unit
    same_q = "Global emissions rose 2.1 percent in 2023 according to the agency."
    echo_claims = [
        {**_mk("Emissions rose 2.1% in 2023", same_q, source_url=f"https://news{i}.example/a", source_class="independent-journalism"), "numbers": [{"value": "2.1", "unit": "%"}], "independence_unit": f"dom:news{i}.example", "echo_group_id": f"eg_{i}"} for i in range(3)
    ]
    g2, stats2 = run_gates(echo_claims, {f"https://news{i}.example/a": same_q for i in range(3)})
    ius = {g.get("independence_unit") for g in g2 if g.get("quote_found")}
    if len(ius) > 1:
        print(f"FAIL: echo collapse left {len(ius)} units for identical quote"); fails += 1
    else:
        print(f"ok: identical quote across 3 domains collapsed to {len(ius)} independence unit")

    # 5. efficacy measurement, primary not opened -> max SINGLE
    eff = _mk("Vaccine efficacy 94.1%", "Efficacy was 94.1% (95% CI 89-97).", type="measurement", claim_class="efficacy", source_class="expert-secondary", cited_primary="Some Trial 2023", numbers=[{"value": "94.1", "unit": "%"}])
    eff["independence_unit"] = "dom:rev.example"
    eff["echo_group_id"] = "eg_eff"
    # two rewrites (different domains) but no opened primary containing "Some Trial 2023"
    eff2 = dict(eff); eff2["source_url"] = "https://rev2.example/x"; eff2["independence_unit"] = "dom:rev2.example"
    g3, _ = run_gates([eff, eff2], {"https://rev.example/x": "Efficacy was 94.1% (95% CI 89-97).", "https://rev2.example/x": "Efficacy was 94.1% (95% CI 89-97)."})
    for g in g3:
        if g.get("status") == "CORROBORATED":
            print("FAIL: efficacy measurement reached CORROBORATED without opened primary"); fails += 1
            break
    else:
        print("ok: efficacy measurement capped at SINGLE without opened primary")

    # 6. number_gate_fail caps an otherwise-CORROBORATED claim to SINGLE
    from .gates import default_status

    c6 = _mk(
        "X reduces mortality 40%",
        "The trial reported no reduction in mortality.",
        numbers=[{"value": "40", "unit": "%"}],
        source_class="peer-reviewed",
    )
    c6["quote_found"] = True
    c6["number_gate_fail"] = True
    if default_status(c6, {"eg": 2}, set()) != "SINGLE":
        print("FAIL: number_gate_fail did not cap to SINGLE"); fails += 1
    else:
        print("ok: number_gate_fail caps to SINGLE")

    # 7. polarity_fail caps an otherwise-CORROBORATED claim to SINGLE
    c7 = _mk(
        "The drug reduces fever",
        "The drug showed no effect on fever.",
        source_class="peer-reviewed",
    )
    c7["quote_found"] = True
    c7["polarity_fail"] = "polarity_mismatch"
    if default_status(c7, {"eg": 2}, set()) != "SINGLE":
        print("FAIL: polarity_fail did not cap to SINGLE"); fails += 1
    else:
        print("ok: polarity_fail caps to SINGLE")

    if fails:
        print(f"\nSELFCHECK FAILED: {fails} issue(s)")
        return 1
    print("\nSELFCHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
