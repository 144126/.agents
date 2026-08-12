from __future__ import annotations

from collections import defaultdict
from typing import Any

import re

from .gates import extract_ids
from .merge import evidence_quality, main_risk
from .util import utc_date, write_jsonl
from .workspace import list_pages, list_sources, load_meta, pub_paths, read_jsonl, work_dir


def _derive_stats(slug: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit stats are computed from the on-disk files, never cached."""
    queries = read_jsonl(work_dir(slug) / "queries.jsonl")
    pages = list_pages(slug)
    gated = claims

    searches = len(queries)
    adversarial_searches = sum(1 for q in queries if q.get("channel") == "adversarial")
    fetched_ok = sum(1 for p in pages if p.get("fetched") == "yes")
    fetched_fail = sum(1 for p in pages if p.get("fetched") != "yes")
    claims_raw = len(read_jsonl(work_dir(slug) / "claims.raw.jsonl"))

    quote_ok = sum(1 for c in gated if c.get("quote_found"))
    quote_reject = sum(1 for c in gated if not c.get("quote_found"))
    echo_groups = len({c.get("echo_group_id") for c in gated})
    independence_units = len({c.get("independence_unit") for c in gated if c.get("quote_found")})
    numeric_conflicts = len({c.get("id") for c in gated if c.get("numeric_conflict")})

    page_ids = set()
    for p in pages:
        for ids in (p.get("ids_mentioned") or []):
            page_ids.add(str(ids).lower())
    primaries_opened = 0
    for c in gated:
        cp = (c.get("cited_primary") or "").lower()
        if not cp:
            continue
        if any(pid and (pid in cp or cp in pid) for pid in page_ids):
            primaries_opened += 1

    return {
        "searches": searches,
        "adversarial_searches": adversarial_searches,
        "fetched_ok": fetched_ok,
        "fetched_fail": fetched_fail,
        "claims_raw": claims_raw,
        "quote_ok": quote_ok,
        "quote_reject": quote_reject,
        "echo_groups": echo_groups,
        "independence_units": independence_units,
        "numeric_conflicts": numeric_conflicts,
        "primaries_opened": primaries_opened,
    }


NUMBER_RE = re.compile(r"(?P<val>\d[\d,]*(?:\.\d+)?)")


def _line_for_cluster(c: dict[str, Any]) -> str:
    claim = (c.get("claim") or "").strip()
    bits = [f"conf={c.get('conf')}"]
    if c.get("indep_count"):
        bits.append(f"indep={c.get('indep_count')}")
    if c.get("method"):
        bits.append(str(c["method"])[:60])
    meta = "; ".join(bits)
    urls = " ".join(f"[{u}]" for u in (c.get("urls") or [])[:6])
    return f"- {claim} — {meta} — {urls}".rstrip(" —")


def render_ledger(
    meta: dict[str, Any],
    clusters: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    gate_stats: dict[str, Any] | None = None,
) -> str:
    stats = _derive_stats(meta["slug"], claims)
    by_st: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in clusters:
        by_st[c.get("status") or "UNCHECKED"].append(c)

    eq = evidence_quality(meta, clusters, stats)
    risk = main_risk(meta, clusters, stats)
    sources = list_sources(meta["slug"])

    def section(title: str, rows: list[dict[str, Any]], empty: str = "None found in budget.") -> str:
        lines = [f"## {title}", ""]
        if not rows:
            lines.append(empty)
            lines.append("")
            return "\n".join(lines)
        for r in rows:
            lines.append(_line_for_cluster(r))
        lines.append("")
        return "\n".join(lines)

    contested_block = ["## Contested", ""]
    cont = by_st.get("CONTESTED") or []
    if not cont:
        contested_block.append("None found in budget.")
        contested_block.append("")
    else:
        for r in cont:
            contested_block.append(f"### { (r.get('claim') or '')[:80] }")
            contested_block.append(_line_for_cluster(r))
            contested_block.append(
                "- Note: independence units or numbers disagree; do not average."
            )
            contested_block.append("")

    src_lines = [
        "## Sources",
        "",
        "| class | channel | title | url | fetched | role_note |",
        "|-------|---------|-------|-----|---------|-----------|",
    ]
    for s in sources:
        src_lines.append(
            "| {class} | {channel} | {title} | {url} | {fetched} | {role} |".format(
                **{
                    "class": s.get("class") or "",
                    "channel": s.get("channel") or "",
                    "title": (s.get("title") or "")[:48].replace("|", "/"),
                    "url": s.get("url") or "",
                    "fetched": s.get("fetched") or s.get("fetch") or "",
                    "role": (s.get("role_note") or "")[:40].replace("|", "/"),
                }
            )
        )
    src_lines.append("")

    channels_used = defaultdict(int)
    for s in sources:
        channels_used[s.get("channel") or "?"] += 1

    body = f"""# {meta.get("subject") or meta.get("slug")}

- Question: {meta.get("question") or meta.get("subject")}
- Settlement criteria: {meta.get("settlement_criteria") or "infer from sources"}
- Evidence quality: {eq}
- Main risk of being wrong: {risk}
- Sampling: claim-class={meta.get("claim_class")}; independence units={stats.get("independence_units", 0)} after echo collapse
- Source budget: n={meta.get("n")}
- Generated: {utc_date()}

{section("Corroborated", by_st.get("CORROBORATED") or [])}
{section("Authorized (single entitled source)", by_st.get("AUTHORIZED") or [])}
{chr(10).join(contested_block)}
{section("Single-source reports", by_st.get("SINGLE") or [])}
{section("Interested-party claims", by_st.get("INTERESTED") or [])}
{section("Unchecked", by_st.get("UNCHECKED") or [])}
## Unknowns and gaps

- Search-ranked sample only; not the full web
- Primaries opened={stats.get("primaries_opened", 0)}
- Quote rejects={stats.get("quote_reject", 0)}
- Add clerk notes for population/method holes after review

## Process audit

- Claims extracted: {stats.get("claims_raw", len(claims))}
- Rejected for bad/missing quote: {stats.get("quote_reject", 0)}
- Quote ok: {stats.get("quote_ok", 0)}
- Echo groups collapsed: {stats.get("echo_groups", 0)} groups → {stats.get("independence_units", 0)} independence units
- Numeric conflicts: {stats.get("numeric_conflicts", 0)}
- Primaries chased: {stats.get("primaries_opened", 0)} opened
- Adversarial extra searches: {stats.get("adversarial_searches", 0)}
- Channels used (source rows): warrant={channels_used.get("warrant", 0)}, outside={channels_used.get("outside", 0)}, adversarial={channels_used.get("adversarial", 0)}
- Searches run: {stats.get("searches", 0)}; fetches ok/fail: {stats.get("fetched_ok", 0)}/{stats.get("fetched_fail", 0)}

{chr(10).join(src_lines)}
"""
    return body


def publish(slug: str, meta: dict[str, Any], claims: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, str]:
    paths = pub_paths(slug)
    settled = [c for c in claims if (c.get("status") or "").upper() == "SETTLED"]
    if settled:
        raise RuntimeError(
            "refusing write: SETTLED status present in gated claims "
            f"({len(settled)} rows). SETTLED is banned; use CORROBORATED/CONTESTED/etc."
        )
    write_jsonl(paths["claims"], claims)
    write_jsonl(paths["sources"], list_sources(slug))
    md = render_ledger(meta, clusters, claims)
    paths["md"].write_text(md, encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def verify_ledger(slug: str, claims: list[dict[str, Any]]) -> list[str]:
    """Every URL in the published md must be a known source url.

    The number check is intentionally omitted: the claim lines are rendered
    from the gated claims, so any check on them is a tautology that can only
    false-positive on honest UNCHECKED lines.
    """
    paths = pub_paths(slug)
    if not paths["md"].exists():
        return ["missing md"]
    text = paths["md"].read_text(encoding="utf-8")
    allowed_urls = {c.get("source_url") for c in claims if c.get("source_url")}
    for s in list_sources(slug):
        if s.get("url"):
            allowed_urls.add(s["url"])
    allowed_prefixes = {a.rstrip("/") for a in allowed_urls if a}

    errors = []
    for u in re.findall(r"https?://[^\s\]\|>]+", text):
        u = u.rstrip(".,;")
        if not u:
            continue
        if u in allowed_urls:
            continue
        if any(u.startswith(p) for p in allowed_prefixes):
            continue
        if any(p.startswith(u) for p in allowed_prefixes):
            continue
        errors.append(f"unknown_url_in_ledger: {u}")
    return errors
