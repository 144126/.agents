from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .util import norm_quote_key, sha1_text


def cluster_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cluster by echo_group primarily; split contested polarity."""
    by_eg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in claims:
        by_eg[c.get("echo_group_id") or f"solo_{c.get('id')}"].append(c)

    clusters = []
    for eg, rows in by_eg.items():
        # representative wording: longest claim among quote_found
        ranked = sorted(
            rows,
            key=lambda r: (
                1 if r.get("quote_found") else 0,
                len(r.get("claim") or ""),
            ),
            reverse=True,
        )
        rep = ranked[0]
        statuses = {r.get("status") for r in rows}
        if "CONTESTED" in statuses:
            status = "CONTESTED"
        elif "CORROBORATED" in statuses:
            status = "CORROBORATED"
        elif "AUTHORIZED" in statuses:
            status = "AUTHORIZED"
        elif "SINGLE" in statuses:
            status = "SINGLE"
        elif "INTERESTED" in statuses:
            status = "INTERESTED"
        else:
            status = "UNCHECKED"

        confs = [r.get("conf") for r in rows if r.get("conf")]
        conf = "low"
        if "high" in confs:
            conf = "high"
        elif "medium" in confs:
            conf = "medium"

        urls = []
        seen = set()
        for r in rows:
            u = r.get("source_url")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)

        units = len({r.get("independence_unit") for r in rows if r.get("quote_found")})
        clusters.append(
            {
                "id": f"cl_{sha1_text(eg)[:10]}",
                "echo_group_id": eg,
                "status": status,
                "conf": conf,
                "claim": rep.get("claim"),
                "type": rep.get("type"),
                "method": rep.get("method"),
                "indep_count": units,
                "urls": urls,
                "claim_ids": [r.get("id") for r in rows if r.get("id")],
                "force_contested": any(r.get("force_contested") for r in rows),
                "numbers": rep.get("numbers") or [],
                "scope": rep.get("scope") or {},
                "channel": rep.get("channel"),
                "source_class": rep.get("source_class"),
                "members": len(rows),
            }
        )
    # sort: corroborated first
    order = {
        "CORROBORATED": 0,
        "AUTHORIZED": 1,
        "CONTESTED": 2,
        "SINGLE": 3,
        "INTERESTED": 4,
        "UNCHECKED": 5,
    }
    clusters.sort(key=lambda c: (order.get(c["status"], 9), -c.get("indep_count", 0)))
    return clusters


def evidence_quality(meta: dict[str, Any], clusters: list[dict[str, Any]], stats: dict[str, Any] | None = None) -> str:
    stats = stats or {}
    corr = sum(1 for c in clusters if c.get("status") == "CORROBORATED")
    auth = sum(1 for c in clusters if c.get("status") == "AUTHORIZED")
    weak = sum(
        1 for c in clusters if c.get("status") in {"SINGLE", "INTERESTED", "UNCHECKED"}
    )
    iff = int(stats.get("quote_reject", 0))
    iunits = int(stats.get("independence_units", 0))
    if corr >= 3 and iunits >= 4 and iff < corr:
        return "strong"
    if corr + auth >= 2 and iunits >= 2:
        return "mixed"
    if weak and not corr:
        return "weak"
    return "mixed"


def main_risk(meta: dict[str, Any], clusters: list[dict[str, Any]], stats: dict[str, Any] | None = None) -> str:
    stats = stats or {}
    parts = []
    if stats.get("quote_reject", 0):
        parts.append(f"{stats['quote_reject']} claims failed quote gate")
    if stats.get("numeric_conflicts", 0):
        parts.append(f"{stats['numeric_conflicts']} numeric conflicts")
    cont = sum(1 for c in clusters if c.get("status") == "CONTESTED")
    if cont:
        parts.append(f"{cont} contested clusters")
    if not parts:
        parts.append("sample is search-ranked pages only; ranks move")
    return "; ".join(parts)
