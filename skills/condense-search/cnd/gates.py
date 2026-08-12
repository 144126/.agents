from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .util import norm_quote_key, norm_ws, registrable_domain, sha1_text

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"\barxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(v\d+)?", re.I)
TRIAL_RE = re.compile(r"\bNCT\d{8}\b", re.I)
DATE_RE = re.compile(r"\b(?:19|20)\d{2}(?:[-/](?:0?[1-9]|1[0-2])(?:[-/](?:0?[1-9]|[12]\d|3[01]))?)?\b")
NUMBER_RE = re.compile(
    r"(?P<val>[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?P<unit>%|x|×|k|m|b|ms|s|tok/s|/\$|/m(?:tok)?|tokens?)?",
    re.I,
)
# negation words that flip polarity
NEG_RE = re.compile(r"\b(no|not|never|without|fail(?:s|ed|ure)?|lack(?:s|ed)?|den(?:ies|y|ied)|absen(?:t|ce)|n't|didn't|doesn't|won't|can't|couldn't|isn't|aren't|wasn't|weren't)\b", re.I)
CAUSE_RE = re.compile(r"\b(caus(?:es|ed|ing)|leads? to|result(?:s|ed)? in|increases?|improves?|reduces?|prevents?|drives?)\b", re.I)


def quote_in_text(quote: str, page_text: str) -> tuple[bool, str]:
    """Return (found, mode) mode in exact|ws|miss.

    CORROBORATED/AUTHORIZED require exact or ws only. A quote that is not a
    verbatim substring (even after whitespace normalization) is rejected.
    """
    q = quote or ""
    t = page_text or ""
    if not q.strip() or not t:
        return False, "miss"
    if q in t:
        return True, "exact"
    nq, nt = norm_ws(q), norm_ws(t)
    if nq and nq in nt:
        return True, "ws"
    return False, "miss"


def _window_around(quote: str, page_text: str, n_sentences: int = 2) -> str:
    """Return the quote sentence plus +/- n_sentences of surrounding context."""
    t = page_text or ""
    if not t:
        return ""
    # locate quote start in text (exact or whitespace-normalized)
    idx = t.find(quote)
    cand = quote
    if idx < 0:
        nq, nt = norm_ws(quote), norm_ws(t)
        idx = nt.find(nq)
        cand = nq
    if idx < 0:
        # fallback: use whole text for containment checks
        return t
    seg_start = max(0, idx - 600)
    seg_end = min(len(t), idx + len(cand) + 600)
    return t[seg_start:seg_end]


def _numbers_in_text(text: str) -> set[str]:
    nums = set()
    for m in NUMBER_RE.finditer(text or ""):
        v = m.group("val").replace(",", "")
        u = (m.group("unit") or "").lower()
        nums.add(f"{v}{('|'+u) if u else ''}")
    return nums


def numbers_match_claim(claim: dict[str, Any], page_text: str) -> tuple[bool, list[str]]:
    """Every parsed number/date in the claim must appear in quote or ±2 sentences.

    Returns (ok, missing) — missing lists the numbers/dates absent from the
    quote window. A claim with no structured numbers is trivially ok.
    """
    window = ""
    q = claim.get("quote") or ""
    q2 = claim.get("quote2")
    if q:
        window += _window_around(q, page_text) + "\n"
    if q2:
        window += _window_around(q2, page_text)
    if not window.strip():
        window = page_text

    hay_nums = _numbers_in_text(window)
    missing = []
    for n in claim.get("numbers") or []:
        if not isinstance(n, dict):
            continue
        v = str(n.get("value", "")).replace(",", "").replace("%", "")
        if not v:
            continue
        u = (str(n.get("unit") or "").lower())
        key = f"{v}{('|'+u) if u else ''}"
        # also accept bare value with any unit
        bare = f"{v}"
        if key not in hay_nums and bare not in hay_nums:
            missing.append(v + (f"{u}" if u else ""))
    # dates in claim text must appear in window
    claim_dates = set(DATE_RE.findall(claim.get("claim") or ""))
    for d in claim_dates:
        if d not in window:
            missing.append(d)
    return (len(missing) == 0), missing


def negation_polarity_ok(claim: dict[str, Any], page_text: str) -> tuple[bool, str]:
    """Quote with negation cannot support a causal/assertive claim and vice versa.

    Returns (ok, reason).
    """
    q = claim.get("quote") or ""
    if not q:
        return True, ""
    claim_text = claim.get("claim") or ""
    quote_neg = bool(NEG_RE.search(q))
    claim_cause = bool(CAUSE_RE.search(claim_text))
    claim_neg = bool(NEG_RE.search(claim_text))
    # "X causes Y" but quote says "no effect" / "does not reduce"
    if claim_cause and quote_neg:
        return False, "polarity_mismatch: claim asserts causation but quote negates"
    # claim denies but quote asserts cause
    if claim_neg and claim_cause is False and quote_neg is False:
        # claim says "no effect" and quote asserts a cause -> mismatch
        if CAUSE_RE.search(q):
            return False, "polarity_mismatch: claim negates but quote asserts cause"
    return True, ""


def gate_quote(claim: dict[str, Any], page_text: str) -> dict[str, Any]:
    out = dict(claim)
    q = out.get("quote") or ""
    ok, mode = quote_in_text(q, page_text)
    if ok and out.get("quote2"):
        ok2, mode2 = quote_in_text(str(out["quote2"]), page_text)
        if not ok2:
            ok, mode = False, "miss"
        else:
            mode = f"{mode}+{mode2}"
    out["quote_found"] = bool(ok)
    out["quote_mode"] = mode

    reasons = list(out.get("gate_reasons") or [])

    if not ok:
        reasons.append("quote_fail")
        out["gate_reasons"] = reasons
        return out

    # number/date containment gate (item 1)
    nums_ok, missing = numbers_match_claim(out, page_text)
    if not nums_ok:
        out["numbers_missing"] = missing
        reasons.append("numbers_not_in_quote")
        out["number_gate_fail"] = True

    # negation polarity gate (item 1)
    pol_ok, pol_reason = negation_polarity_ok(out, page_text)
    if not pol_ok:
        out["polarity_fail"] = pol_reason
        reasons.append("polarity_fail")

    out["gate_reasons"] = reasons
    return out


def number_signature(claim: dict[str, Any]) -> str:
    nums = claim.get("numbers") or []
    parts = []
    for n in nums:
        if not isinstance(n, dict):
            continue
        v = str(n.get("value", "")).replace(",", "")
        u = str(n.get("unit") or "").lower()
        st = str(n.get("stat") or "").lower()
        parts.append(f"{v}|{u}|{st}")
    if parts:
        return ";".join(sorted(parts))
    # fallback: harvest from claim text
    found = []
    for m in NUMBER_RE.finditer(claim.get("claim") or ""):
        found.append(m.group(0).lower().replace(" ", ""))
    return ";".join(found[:6])


def extract_ids(text: str) -> list[str]:
    ids = []
    for rx in (DOI_RE, TRIAL_RE):
        ids.extend(m.group(0).lower() for m in rx.finditer(text or ""))
    for m in ARXIV_RE.finditer(text or ""):
        ids.append(f"arxiv:{m.group(1)}")
    return sorted(set(ids))


def echo_key(claim: dict[str, Any]) -> str:
    """Collapse key: shared primary id OR strong number signature OR stem+num.

    Extended (item 3): near-identical norm_quote_key across domains collapses
    to one independence unit; shared cited_primary + same number also collapses.
    """
    blob = " ".join(
        [
            claim.get("claim") or "",
            claim.get("quote") or "",
            claim.get("cited_primary") or "",
            " ".join(claim.get("derived_from") or []),
        ]
    )
    ids = extract_ids(blob)
    if ids:
        return "id:" + ids[0]
    # shared cited primary + same number -> one echo family
    ns = number_signature(claim)
    if claim.get("cited_primary") and ns:
        return f"primary:{norm_quote_key(str(claim.get('cited_primary'))[:24])}|{ns}"
    # near-identical quote (compressed alnum) across rewrites -> one unit
    qk = norm_quote_key(claim.get("quote") or "")
    if len(qk) >= 24:
        return f"qk:{qk[:32]}"
    ns = number_signature(claim)
    polarity = (claim.get("stance") or "asserts")[0]
    if ns and any("|" in part for part in ns.split(";")):
        scope = claim.get("scope") or {}
        pop = norm_quote_key(str(scope.get("population") or ""))[:12]
        return f"num:{ns}|pop:{pop}|p:{polarity}"
    # no shared id / primary / verbatim quote / structured number -> distinct
    return f"claim:{sha1_text((claim.get('claim') or '') + (claim.get('source_url') or ''))[:12]}"


def independence_unit_for(claim: dict[str, Any], echo_group: str) -> str:
    if echo_group.startswith("id:"):
        return echo_group
    if echo_group.startswith("qk:") or echo_group.startswith("primary:"):
        # wire rewrite across domains collapses to one unit (item 3)
        return echo_group
    url = claim.get("source_url") or ""
    cls = (claim.get("source_class") or "").lower()
    dom = registrable_domain(url)
    if cls in {"vendor-marketing", "originator"} and dom:
        return f"org:{dom}"
    if dom:
        return f"dom:{dom}"
    return f"url:{sha1_text(url)[:10]}"


def assign_echo_groups(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(list)
    keys = []
    for i, c in enumerate(claims):
        k = echo_key(c)
        keys.append(k)
        groups[k].append(i)
    out = []
    for i, c in enumerate(claims):
        cc = dict(c)
        eg = f"eg_{sha1_text(keys[i])[:10]}"
        cc["echo_group_id"] = eg
        cc["echo_key"] = keys[i]
        cc["independence_unit"] = independence_unit_for(cc, keys[i])
        out.append(cc)
    return out


def parse_num_value(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def numeric_conflict_key(claim: dict[str, Any], num: dict[str, Any]) -> str:
    stat = str(num.get("stat") or "").lower()
    unit = str(num.get("unit") or "").lower()
    # bucket only when a stat is named; a bare unit ("%") groups unrelated
    # quantities (efficacy vs mortality) and produces false conflicts.
    if not stat:
        return ""
    scope = claim.get("scope") or {}
    pop = str(scope.get("population") or "")[:40].lower()
    return f"{stat}|{unit}|{pop}"


def find_numeric_conflicts(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same quantity key, incompatible values across independence units → conflict."""
    buckets: dict[str, list[tuple[dict, dict, float]]] = defaultdict(list)
    for c in claims:
        if not c.get("quote_found"):
            continue
        for n in c.get("numbers") or []:
            if not isinstance(n, dict):
                continue
            v = parse_num_value(n.get("value"))
            if v is None:
                continue
            k = numeric_conflict_key(c, n)
            if not k:
                continue
            buckets[k].append((c, n, v))

    conflicts = []
    for k, rows in buckets.items():
        by_unit: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
        for c, n, v in rows:
            iu = c.get("independence_unit") or c.get("source_url") or ""
            by_unit[iu].append((v, c.get("source_url") or "", c.get("id") or ""))
        unit_vals = []
        for iu, vals in by_unit.items():
            unit_vals.append((iu, vals[0][0], vals[0][1]))
        if len(unit_vals) < 2:
            continue
        values = [v for _, v, _ in unit_vals]
        lo, hi = min(values), max(values)
        if lo == hi:
            continue
        rel = abs(hi - lo) / max(abs(lo), 1e-9)
        abs_diff = abs(hi - lo)
        if rel < 0.05 or abs_diff < 0.5:
            continue
        conflicts.append(
            {
                "key": k,
                "values": [
                    {"independence_unit": iu, "value": v, "url": u}
                    for iu, v, u in unit_vals
                ],
            }
        )
    return conflicts


def apply_numeric_conflicts(
    claims: list[dict[str, Any]], conflicts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not conflicts:
        return claims
    conflict_keys = {conf["key"] for conf in conflicts}
    out = []
    for c in claims:
        cc = dict(c)
        for n in cc.get("numbers") or []:
            if isinstance(n, dict) and numeric_conflict_key(cc, n) in conflict_keys:
                reasons = list(cc.get("gate_reasons") or [])
                if "numeric_conflict" not in reasons:
                    reasons.append("numeric_conflict")
                cc["gate_reasons"] = reasons
                cc["numeric_conflict"] = True
                cc["force_contested"] = True
                break
        out.append(cc)
    return out


def _primary_opened(claim: dict[str, Any], opened_primaries: set[str]) -> bool:
    """A claim's primary is opened if its cited_primary id matches an opened url/page."""
    cp = (claim.get("cited_primary") or "").lower()
    if not cp:
        return False
    for op in opened_primaries:
        if op and op.lower() in cp or cp in op.lower():
            return True
    return cp in opened_primaries


def default_status(claim: dict[str, Any], unit_support: dict[str, int], opened_primaries: set[str]) -> str:
    if not claim.get("quote_found"):
        return "UNCHECKED"
    if claim.get("number_gate_fail") or claim.get("polarity_fail"):
        # a claim whose numbers aren't in the quote, or whose polarity
        # contradicts its quote, cannot earn high status
        cls = (claim.get("source_class") or "").lower()
        return "INTERESTED" if cls == "vendor-marketing" else "SINGLE"
    cls = (claim.get("source_class") or "").lower()
    if cls in {"vendor-marketing"}:
        return "INTERESTED"
    if claim.get("force_contested"):
        return "CONTESTED"
    eg = claim.get("echo_group_id") or ""
    units = unit_support.get(eg, 1)

    # hard primary cap (item 5): measurement claim-class efficacy + no opened
    # primary -> max SINGLE even with multiple rewrites
    claim_class = (claim.get("claim_class") or "").lower()
    is_efficacy_measurement = (
        claim_class == "efficacy" and claim.get("type") == "measurement"
    )
    primary_open = _primary_opened(claim, opened_primaries)

    if units <= 1 and cls in {"originator", "primary-data", "official", "peer-reviewed"}:
        if is_efficacy_measurement and not primary_open:
            return "SINGLE"
        if cls == "originator":
            return "AUTHORIZED"
        if cls in {"primary-data", "official"}:
            return "AUTHORIZED"
        return "SINGLE"

    if units >= 2 and cls not in {"vendor-marketing"}:
        if is_efficacy_measurement and not primary_open:
            return "SINGLE"
        return "CORROBORATED"

    if units <= 1:
        if cls in {"vendor-marketing"}:
            return "INTERESTED"
        if is_efficacy_measurement and not primary_open:
            return "SINGLE"
        return "SINGLE"
    return "SINGLE"


def confidence_for(status: str, claim: dict[str, Any], units: int) -> str:
    if status in {"UNCHECKED", "INTERESTED"}:
        return "low"
    if status == "CONTESTED":
        return "medium"
    if status == "CORROBORATED":
        if units >= 3 and claim.get("method"):
            return "high"
        if units >= 2 and claim.get("method"):
            return "high"
        if units >= 2:
            return "medium"
        return "medium"
    if status == "AUTHORIZED":
        return "high" if (claim.get("source_class") or "") in {
            "originator",
            "primary-data",
            "official",
        } else "medium"
    return "low"


def assign_status(
    claims: list[dict[str, Any]], opened_primaries: set[str] | None = None
) -> list[dict[str, Any]]:
    opened_primaries = opened_primaries or set()
    by_eg: dict[str, set[str]] = defaultdict(set)
    for c in claims:
        if not c.get("quote_found"):
            continue
        eg = c.get("echo_group_id") or ""
        iu = c.get("independence_unit") or ""
        cls = (c.get("source_class") or "").lower()
        if cls == "vendor-marketing":
            continue
        by_eg[eg].add(iu)
    unit_counts = {eg: max(1, len(s)) for eg, s in by_eg.items()}

    stance_by_eg: dict[str, set[str]] = defaultdict(set)
    for c in claims:
        if not c.get("quote_found"):
            continue
        eg = c.get("echo_group_id") or ""
        stance_by_eg[eg].add(c.get("stance") or "asserts")

    out = []
    for c in claims:
        cc = dict(c)
        eg = cc.get("echo_group_id") or ""
        units = unit_counts.get(eg, 1)
        stances = stance_by_eg.get(eg, set())
        # a claim whose numbers aren't in the quote, or whose polarity
        # contradicts its quote, is unsupported -> SINGLE, not CONTESTED.
        if cc.get("number_gate_fail") or cc.get("polarity_fail"):
            status = default_status(cc, unit_counts, opened_primaries)
        elif cc.get("force_contested") or (
            "asserts" in stances and "denies" in stances
        ):
            status = "CONTESTED" if cc.get("quote_found") else "UNCHECKED"
        else:
            status = default_status(cc, unit_counts, opened_primaries)
        # encyclopedia alone cannot CORROBORATE measurements
        if (
            status == "CORROBORATED"
            and (cc.get("type") == "measurement")
            and (cc.get("source_class") or "").lower() == "expert-secondary"
            and units < 2
        ):
            status = "SINGLE"
        cc["status"] = status
        cc["conf"] = confidence_for(status, cc, units)
        cc["indep_count"] = units
        out.append(cc)

    return out


def run_gates(
    claims: list[dict[str, Any]], page_text_by_url: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quoted = []
    q_ok = q_bad = 0
    for c in claims:
        url = c.get("source_url") or ""
        text = page_text_by_url.get(url) or ""
        g = gate_quote(c, text)
        if g.get("quote_found"):
            q_ok += 1
        else:
            q_bad += 1
        quoted.append(g)

    echoed = assign_echo_groups(quoted)
    conflicts = find_numeric_conflicts(echoed)
    numbered = apply_numeric_conflicts(echoed, conflicts)

    # opened primaries = primary ids (DOI/NCT/arxiv) actually present in a
    # fetched page; a primary is "opened" only if its id appears in a page we
    # fetched, not merely because a secondary mentions it.
    opened: set[str] = set()
    for txt in page_text_by_url.values():
        opened |= set(extract_ids(txt))
    final = assign_status(numbered, opened)

    egs = {c.get("echo_group_id") for c in final}
    ius = {c.get("independence_unit") for c in final if c.get("quote_found")}
    stats = {
        "quote_ok": q_ok,
        "quote_reject": q_bad,
        "echo_groups": len(egs),
        "independence_units": len(ius),
        "numeric_conflicts": len(conflicts),
        "conflicts": conflicts,
    }
    return final, stats
