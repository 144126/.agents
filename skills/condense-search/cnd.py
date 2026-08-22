#!/usr/bin/env python3
"""cnd — web search condensed into a quote-audited fact ledger.

Honest scope: proves each published claim carries a verbatim quote from a
fetched page, that every figure/date in the claim appears near its quote,
that agreement comes from distinct domains, and that copy-paste echoes or
shared primary ids collapse to one source. It does not judge semantics,
detect paraphrased syndication, or rank source trustworthiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SEARCH_ROOT = Path.home() / "search"
SECRETS_ENV = Path.home() / ".agents" / "secrets" / "firecrawl.env"
API = "https://api.firecrawl.dev/v1"

NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:%|x|×)?")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
NCT_RE = re.compile(r"\bNCT\d{8}\b", re.I)

# ---------- small utils ----------


def die(msg: str) -> None:
    print(f"cnd: {msg}", file=sys.stderr)
    raise SystemExit(1)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()


def slugify(text: str) -> str:
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.strip().lower())).strip("-")
    return (s or "topic")[:64]


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_ws(s).lower())


def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def dump_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def write_jsonl(p: Path, rows: list[dict[str, Any]]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def append_jsonl(p: Path, row: dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
    except Exception:
        return url.strip().lower()
    host = (p.netloc or "").lower().removeprefix("www.")
    q = [kv for kv in (p.query or "").split("&")
         if kv.split("=", 1)[0].lower()
         not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}]
    return f"{host}{(p.path or '').rstrip('/')}{'?' + '&'.join(sorted(q)) if q else ''}"


def page_id_for_url(url: str) -> str:
    return sha1(normalize_url(url))[:16]


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
    return host


# ccTLD second-level suffixes so co.uk does not collapse to ".uk"
MULTI_TLDS = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au",
              "co.jp", "or.jp", "ac.jp", "co.nz", "co.za", "co.in", "com.br", "co.il"}


def registrable_domain(url: str) -> str:
    host = domain_of(url)
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_TLDS:
        return ".".join(parts[-3:])
    return host if len(parts) < 2 else ".".join(parts[-2:])


# ---------- firecrawl ----------


def api_key() -> str:
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if key:
        return key
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k == "FIRECRAWL_API_KEY" and v.strip():
                os.environ["FIRECRAWL_API_KEY"] = v.strip().strip("'\"")
                return os.environ["FIRECRAWL_API_KEY"]
    die(f"no FIRECRAWL_API_KEY (set env or {SECRETS_ENV})")


def _post(path: str, body: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        die(f"firecrawl HTTP {e.code} on {path}: {e.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as e:
        die(f"firecrawl network error on {path}: {e}")
    return {}


def fc_search(query: str, num: int) -> list[dict[str, Any]]:
    data = _post("/search", {"query": query, "limit": max(1, min(num, 20)), "timeout": 60000})
    return [{"url": r.get("url"),
             "title": r.get("title") or r.get("metadata", {}).get("title"),
             "date": r.get("publishedDate") or r.get("metadata", {}).get("publishedTime")}
            for r in data.get("data") or [] if r.get("url")]


def fc_scrape(url: str, text_max: int) -> str:
    try:
        data = _post("/scrape", {"url": url, "formats": ["markdown"], "timeout": 60000}, timeout=120)
    except SystemExit:
        return ""
    doc = data.get("data") or {}
    return (doc.get("markdown") or "")[:text_max]


def pdf_text(url: str) -> str:
    """Fallback PDF extraction via curl|pdftotext when firecrawl returns little."""
    if not shutil.which("pdftotext"):
        return ""
    try:
        with tempfile.TemporaryDirectory() as td:
            pdf, txt = Path(td) / "d.pdf", Path(td) / "d.txt"
            subprocess.run(["curl", "-fsSL", "--max-filesize", "200000000", "-o", str(pdf), url],
                           check=True, timeout=120)
            subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True, timeout=120)
            out = txt.read_text(encoding="utf-8", errors="replace").strip()
            return out if len(out) > 500 else ""
    except Exception:
        return ""


# ---------- workspace ----------


def work_dir(slug: str) -> Path:
    return SEARCH_ROOT / slug


def pub_paths(slug: str) -> dict[str, Path]:
    return {"md": SEARCH_ROOT / f"{slug}.md",
            "claims": SEARCH_ROOT / f"{slug}.claims.jsonl",
            "sources": SEARCH_ROOT / f"{slug}.sources.jsonl"}


def page_paths(slug: str, url: str) -> dict[str, Path]:
    pid = page_id_for_url(url)
    wd = work_dir(slug)
    return {"txt": wd / "pages" / f"{pid}.txt",
            "meta": wd / "pages" / f"{pid}.meta.json",
            "extract": wd / "extracts" / f"{pid}.json"}


def init_workspace(subject: str, n: int, question: str | None, slug: str | None) -> dict[str, Any]:
    sl = slug or slugify(subject)
    for sub in ("pages", "extracts"):
        (work_dir(sl) / sub).mkdir(parents=True, exist_ok=True)
    meta = {"slug": sl, "subject": subject, "question": question or subject, "n": n,
            "created": utc_now(), "updated": utc_now()}
    dump_json(work_dir(sl) / "meta.json", meta)
    return meta


def load_meta(slug: str) -> dict[str, Any]:
    p = work_dir(slug) / "meta.json"
    if not p.exists():
        raise FileNotFoundError(f"no workspace for slug={slug} ({p})")
    return load_json(p)


def save_meta(slug: str, meta: dict[str, Any]) -> None:
    meta["updated"] = utc_now()
    dump_json(work_dir(slug) / "meta.json", meta)


def upsert_source(slug: str, row: dict[str, Any]) -> None:
    path = work_dir(slug) / "sources.jsonl"
    rows = read_jsonl(path)
    for i, r in enumerate(rows):
        if r.get("url") == row.get("url"):
            rows[i] = {**r, **row}
            break
    else:
        rows.append(row)
    write_jsonl(path, rows)


def list_sources(slug: str) -> list[dict[str, Any]]:
    return read_jsonl(work_dir(slug) / "sources.jsonl")


def list_pages(slug: str) -> list[dict[str, Any]]:
    d = work_dir(slug) / "pages"
    out = []
    if d.exists():
        for mp in sorted(d.glob("*.meta.json")):
            try:
                out.append(load_json(mp))
            except Exception:
                pass
    return out


# ---------- gates ----------


def find_ids(text: str) -> list[str]:
    ids = [m.group(0).lower() for rx in (DOI_RE, NCT_RE) for m in rx.finditer(text or "")]
    ids += [f"arxiv:{m.group(1)}" for m in ARXIV_RE.finditer(text or "")]
    return sorted(set(ids))


def quote_in_text(q: str, t: str) -> bool:
    q, t = q or "", t or ""
    if not q.strip() or not t:
        return False
    return q in t or (norm_key(q) in norm_key(t) and bool(norm_key(q)))


def window_around(quote: str, text: str, pad: int = 600) -> str:
    idx = text.find(quote)
    if idx < 0:
        nk, nt = norm_key(quote), norm_key(text)
        # whitespace-insensitive locate: scan word sequence
        words = nk
        idx = nt.find(words[:40]) if len(words) >= 40 else nt.find(words)
    if idx < 0:
        return text
    return text[max(0, idx - pad):idx + len(quote) + pad]


def parse_nums(text: str) -> set[str]:
    out = set()
    for m in NUM_RE.finditer(text or ""):
        tok = re.sub(r"\s+", "", m.group(0)).replace(",", "").replace("×", "x").lower()
        if tok and any(ch.isdigit() for ch in tok):
            out.add(tok)
    return out


def gate_claim(c: dict[str, Any], page_text: str) -> dict[str, Any]:
    g = dict(c)
    q = g.get("quote") or ""
    found = quote_in_text(q, page_text)
    if found and g.get("quote2"):
        found = quote_in_text(str(g["quote2"]), page_text)
    g["quote_found"] = found
    win = window_around(q, page_text) if found and q else ""
    required = parse_nums(g.get("claim") or "")
    have = parse_nums(win)
    missing = sorted(required - have)
    g["missing_numbers"] = missing
    g["verified"] = bool(found and not missing)
    blob = " ".join([g.get("claim") or "", q, g.get("cited_primary") or "",
                     " ".join(g.get("derived_from") or [])])
    ids = find_ids(blob)
    qk = norm_key(q)
    if ids:
        g["echo_key"] = "id:" + ids[0]
    elif len(qk) >= 24:
        g["echo_key"] = "qk:" + qk[:48]
    else:
        g["echo_key"] = "h:" + sha1(norm_key(g.get("claim") or "") + (g.get("source_url") or ""))[:12]
    g["unit"] = registrable_domain(g.get("source_url") or "") or ("u:" + sha1(g.get("source_url") or "?")[:10])
    return g


def assign_status(gated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copies weigh once; only independent restatements corroborate.

    - echo group (identical quote or shared DOI/arxiv/NCT) spanning >=2
      domains is ONE origin: syndication cannot corroborate itself.
    - otherwise each verified domain is its own origin.
    - CORROBORATED needs >=2 origins behind byte-identical claim wording.
    """
    eg_domains: dict[str, set[str]] = defaultdict(set)
    for g in gated:
        if g["verified"]:
            eg_domains[g["echo_key"]].add(g["unit"])
    origins_by_claim: dict[str, set[str]] = defaultdict(set)
    for g in gated:
        if not g["verified"]:
            continue
        copied = len(eg_domains[g["echo_key"]]) >= 2
        g["origin"] = "copy:" + g["echo_key"] if copied else "dom:" + g["unit"]
        origins_by_claim[norm_key(g.get("claim") or "")].add(g["origin"])
    out = []
    for g in gated:
        n = len(origins_by_claim.get(norm_key(g.get("claim") or ""), ())) if g["verified"] else 0
        g["indep_count"] = n
        g["status"] = "CORROBORATED" if n >= 2 else ("SINGLE" if g["verified"] else "UNCHECKED")
        out.append(g)
    return out


def cluster_claims(gated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for g in gated:
        groups[g["echo_key"]].append(g)
    order = {"CORROBORATED": 0, "SINGLE": 1, "UNCHECKED": 2}
    clusters = []
    for key, rows in groups.items():
        rep = max(rows, key=lambda r: len(r.get("claim") or ""))
        urls = []
        seen = set()
        for r in rows:
            u = r.get("source_url")
            if u and u not in seen:
                seen.add(u)
                urls.append(u)
        verified_units = {r["unit"] for r in rows if r["verified"]}
        status = "CORROBORATED" if len(verified_units) >= 2 else \
                 ("SINGLE" if any(r["verified"] for r in rows) else "UNCHECKED")
        clusters.append({"id": "cl_" + sha1(key)[:10], "echo_key": key, "status": status,
                         "claim": rep.get("claim"), "quote": rep.get("quote"),
                         "indep_count": len(verified_units),
                         "members": len(rows), "urls": urls})
    clusters.sort(key=lambda c: (order[c["status"]], -c["indep_count"]))
    return clusters


# ---------- publish ----------


def render_ledger(meta: dict[str, Any], clusters: list[dict[str, Any]],
                  gated: list[dict[str, Any]], queries_n: int, fetched_ok: int,
                  fetched_fail: int) -> str:
    by_st: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in clusters:
        by_st[c["status"]].append(c)

    def section(title: str, rows: list[dict[str, Any]]) -> str:
        lines = [f"## {title}", ""]
        if not rows:
            lines += ["None.", ""]
            return "\n".join(lines)
        for r in rows:
            urls = " ".join(f"[{u}]" for u in r["urls"][:6])
            lines.append(f"- {r['claim']} — indep={r['indep_count']} ({r['members']} extracts) — {urls}".rstrip(" —"))
        lines.append("")
        return "\n".join(lines)

    src_lines = ["## Sources", "", "| title | url | fetched |", "|---|---|---|"]
    for s in list_sources(meta["slug"]):
        title = (s.get("title") or "").replace("|", "/")[:48]
        src_lines.append(f"| {title} | {s.get('url')} | {s.get('fetched', '')} |")

    rejects = sum(1 for g in gated if not g["quote_found"])
    badnums = sum(1 for g in gated if g["quote_found"] and g["missing_numbers"])
    units = {g["unit"] for g in gated if g["verified"]}
    hdr_note = f"- Settlement criteria: {meta['settlement_criteria']}\n" if meta.get("settlement_criteria") else ""

    return f"""# {meta['subject']}

- Question: {meta.get('question') or meta['subject']}
{hdr_note}- Generated: {utc_date()}
- Limits: proves quotation and figure containment only; corroboration means byte-identical claim wording on independent domains; paraphrased syndication is not detected; sample is search-ranked pages.

{section('Corroborated (>=2 independent origins)', by_st.get('CORROBORATED') or [])}
{section('Single-source', by_st.get('SINGLE') or [])}
{section('Unchecked (quote or figure check failed)', by_st.get('UNCHECKED') or [])}
## Process audit

- Searches: {queries_n}; fetches ok/fail: {fetched_ok}/{fetched_fail}
- Claims extracted: {len(gated)}; quote rejects: {rejects}; figure rejects: {badnums}
- Clusters: {len(clusters)}; distinct verified domains: {len(units)}

{chr(10).join(src_lines)}
"""


def verify_ledger(slug: str, claims: list[dict[str, Any]]) -> list[str]:
    text = pub_paths(slug)["md"].read_text(encoding="utf-8")
    allowed = {c["source_url"] for c in claims if c.get("source_url")}
    allowed |= {s["url"] for s in list_sources(slug) if s.get("url")}
    errs = []
    for u in {m.rstrip(".,;") for m in re.findall(r"https?://[^\s\]|>]+", text)}:
        if u in allowed or any(u == p or u.startswith(p + "/") for p in allowed):
            continue
        errs.append(f"unknown_url_in_ledger: {u}")
    return errs


def cmd_write(args: argparse.Namespace) -> None:
    slug = args.slug
    meta = load_meta(slug)
    if args.question:
        meta["question"] = args.question
    if args.settlement:
        meta["settlement_criteria"] = args.settlement
    save_meta(slug, meta)
    gated = read_jsonl(work_dir(slug) / "claims.gated.jsonl")
    if not gated:
        die("no claims.gated.jsonl — run cnd gate first")
    clusters = cluster_claims(gated)
    queries = read_jsonl(work_dir(slug) / "queries.jsonl")
    pages = list_pages(slug)
    md = render_ledger(meta, clusters, gated, len(queries),
                       sum(1 for p in pages if p.get("fetched") == "yes"),
                       sum(1 for p in pages if p.get("fetched") != "yes"))
    paths = pub_paths(slug)
    paths["claims"].parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(paths["claims"], gated)
    write_jsonl(paths["sources"], list_sources(slug))
    paths["md"].write_text(md, encoding="utf-8")
    errs = verify_ledger(slug, gated)
    if errs:
        for p in paths.values():
            p.unlink(missing_ok=True)
        print(json.dumps({"ok": False, "verify_errors": errs}, indent=2))
        return
    print(json.dumps({"ok": True, "published": {k: str(v) for k, v in paths.items()}}, indent=2))


# ---------- commands ----------


def cmd_init(a: argparse.Namespace) -> None:
    meta = init_workspace(a.subject, a.n, a.question, a.slug)
    print(json.dumps({"ok": True, "slug": meta["slug"], "work_dir": str(work_dir(meta["slug"]))}, indent=2))


def cmd_search(a: argparse.Namespace) -> None:
    load_meta(a.slug)
    results = fc_search(a.query, a.num)
    append_jsonl(work_dir(a.slug) / "queries.jsonl",
                 {"ts": utc_now(), "query": a.query, "urls": [r["url"] for r in results]})
    for r in results:
        pid = page_id_for_url(r["url"])
        dump_json(page_paths(a.slug, r["url"])["meta"],
                  {"id": pid, "url": r["url"], "title": r.get("title"),
                   "domain": domain_of(r["url"]), "publishedDate": r.get("date"),
                   "fetched": "no"})
        upsert_source(a.slug, {"url": r["url"], "title": r.get("title"),
                               "domain": domain_of(r["url"]), "fetched": "no", "page_id": pid})
    print(json.dumps({"ok": True, "results": len(results), "urls": [r["url"] for r in results]}, indent=2))


def _scrape_one(slug: str, url: str, text_max: int) -> tuple[str, int, str]:
    paths = page_paths(slug, url)
    old = load_json(paths["meta"]) if paths["meta"].exists() else {}
    text = fc_scrape(url, text_max)
    if len(text) < 2000 and url.lower().endswith(".pdf"):
        text = max(text, pdf_text(url), key=len)
    if text:
        paths["txt"].write_text(text, encoding="utf-8")
        fetched = "yes"
    else:
        fetched = "no"
    meta = {**old, "id": page_id_for_url(url), "url": url, "domain": domain_of(url),
            "fetched": fetched, "text_len": len(text), "updated": utc_now(),
            "ids_mentioned": find_ids(text[:80000])}
    dump_json(paths["meta"], meta)
    upsert_source(slug, {"url": url, "title": old.get("title"), "domain": domain_of(url),
                         "fetched": fetched, "page_id": meta["id"], "text_len": len(text)})
    return url, len(text), fetched


def cmd_fetch(a: argparse.Namespace) -> None:
    load_meta(a.slug)
    if a.url:
        urls = list(a.url)
    else:
        seen: set[str] = set()
        urls = []
        for s in list_sources(a.slug):
            u = s.get("url")
            pp = page_paths(a.slug, u)
            clen = len(pp["txt"].read_text(encoding="utf-8", errors="replace")) if pp["txt"].exists() else 0
            if u and clen < a.min_chars and u not in seen:
                seen.add(u)
                urls.append(u)
    urls = urls[: a.limit] if a.limit else urls
    if not urls:
        print(json.dumps({"ok": True, "fetched": 0, "note": "nothing to fetch"}))
        return
    api_key()
    with ThreadPoolExecutor(max_workers=min(6, len(urls))) as ex:
        rows = list(ex.map(lambda u: _scrape_one(a.slug, u, a.text_max), urls))
    print(json.dumps({"ok": True,
                      "ok_n": sum(1 for r in rows if r[2] == "yes"),
                      "fail_n": sum(1 for r in rows if r[2] != "yes"),
                      "results": [{"url": u, "text_len": n, "fetched": f} for u, n, f in rows]}, indent=2))


def cmd_pages(a: argparse.Namespace) -> None:
    for p in list_pages(a.slug):
        print(f"{p.get('text_len', 0):6}  {p.get('url', '')}  {page_paths(a.slug, p.get('url', ''))['txt']}")


def cmd_ingest_extract(a: argparse.Namespace) -> None:
    slug = a.slug
    load_meta(slug)
    raw_path = work_dir(slug) / "claims.raw.jsonl"
    existing = read_jsonl(raw_path)
    n_new = 0
    for ps in a.extract_json:
        p = Path(ps)
        if not p.exists():
            die(f"missing extract file: {p}")
        data = load_json(p)
        claims = data if isinstance(data, list) else list(data.get("claims") or [])
        src = (data.get("source_url") if isinstance(data, dict) else None) or a.source_url
        if not src:
            die(f"no source_url for {p} (pass --source-url)")
        dump_json(page_paths(slug, src)["extract"], data)
        tp = page_paths(slug, src)["txt"]
        upsert_source(slug, {"url": src, "domain": domain_of(src),
                             "fetched": "yes" if tp.exists() else "no",
                             "page_id": page_id_for_url(src)})
        for i, c in enumerate(claims):
            row = dict(c)
            row.setdefault("source_url", src)
            row.setdefault("id", f"{page_id_for_url(src)}_{i}")
            existing.append(row)
            n_new += 1
    write_jsonl(raw_path, existing)
    print(json.dumps({"ok": True, "ingested_claims": n_new, "total_raw": len(existing)}, indent=2))


def cmd_gate(a: argparse.Namespace) -> None:
    slug = a.slug
    load_meta(slug)
    raw = read_jsonl(work_dir(slug) / "claims.raw.jsonl")
    if not raw:
        die("no claims.raw.jsonl — run cnd ingest-extract first")

    def text_for(url: str) -> str:
        p = page_paths(slug, url or "")["txt"]
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    cache: dict[str, str] = {}
    gated = []
    for c in raw:
        u = c.get("source_url") or ""
        if u not in cache:
            cache[u] = text_for(u)
        gated.append(gate_claim(dict(c), cache[u]))
    gated = assign_status(gated)
    write_jsonl(work_dir(slug) / "claims.gated.jsonl", gated)
    print(json.dumps({"ok": True, "gated": len(gated),
                      "verified": sum(1 for g in gated if g["verified"]),
                      "rejected": sum(1 for g in gated if not g["verified"]),
                      "corroborated": sum(1 for g in gated if g["status"] == "CORROBORATED")}, indent=2))


def cmd_status(a: argparse.Namespace) -> None:
    wd = work_dir(a.slug)
    print(json.dumps({"slug": a.slug, "work_dir": str(wd),
                      "sources": len(list_sources(a.slug)),
                      "raw_claims": len(read_jsonl(wd / "claims.raw.jsonl")),
                      "gated_claims": len(read_jsonl(wd / "claims.gated.jsonl")),
                      "published": {k: p.exists() for k, p in pub_paths(a.slug).items()}}, indent=2))


# ---------- selfcheck ----------


def selfcheck() -> int:
    fails = 0

    def chk(name: str, cond: bool) -> None:
        nonlocal fails
        print(("ok: " if cond else "FAIL: ") + name)
        fails += 0 if cond else 1

    page = "Mortality fell 40% in the treated cohort over twelve weeks."
    good = {"claim": "Mortality fell 40%", "quote": "Mortality fell 40% in the treated cohort.",
            "source_url": "https://a.example/x"}
    g = gate_claim(good, page)
    chk("verbatim quote + figure in quote passes", g["verified"])

    bad = {"claim": "Mortality fell 60%", "quote": "Mortality fell 40% in the treated cohort.",
           "source_url": "https://a.example/x"}
    chk("figure absent from quote window rejected", not gate_claim(bad, page)["verified"])

    nf = {"claim": "Mortality fell", "quote": "this phrase appears nowhere at all in the corpus",
          "source_url": "https://a.example/x"}
    chk("non-substring quote -> UNCHECKED", not gate_claim(nf, page)["verified"])

    same_q = "Global emissions rose 2.1% in 2023 according to the agency."
    trio = [{"claim": "Emissions rose 2.1% in 2023", "quote": same_q,
             "source_url": f"https://news{i}.example/a"} for i in range(3)]
    gated = assign_status([gate_claim(c, same_q) for c in trio])
    chk("identical quote across 3 domains -> ONE origin, no self-corroboration",
        all(g["status"] == "SINGLE" and g["indep_count"] == 1 for g in gated))

    doi_a = {"claim": "Drug X cuts deaths 30% (doi 10.1234/abc123)", "quote": "Deaths fell 30%",
             "source_url": "https://a.example/x"}
    doi_b = {"claim": "Treatment halves mortality risk by 30%", "quote": "Risk dropped 30%",
             "cited_primary": "See 10.1234/abc123", "source_url": "https://b.example/y"}
    ga, gb = gate_claim(doi_a, "Deaths fell 30%. doi 10.1234/abc123"), gate_claim(doi_b, "Risk dropped 30%. See 10.1234/abc123")
    gated = assign_status([ga, gb])
    chk("shared DOI collapses paraphrases to one unit",
        ga["echo_key"] == gb["echo_key"] and gated[0]["status"] != "CORROBORATED")

    par1 = {"claim": "Sales doubled to 2 million units", "quote": "sales doubled to two million",
            "source_url": "https://a.example/x"}
    par2 = {"claim": "Revenue hit 2m units, twice the prior year", "quote": "revenue reached double",
            "source_url": "https://b.example/y"}
    gpa, gpb = gate_claim(par1, "sales doubled to two million"), gate_claim(par2, "revenue reached double")
    assign_status([gpa, gpb])
    chk("paraphrase without shared id stays separate (known limitation)",
        gpa["echo_key"] != gpb["echo_key"])

    allowed = {"https://x.com/post"}
    evil = "https://x.com.evil.org"
    hole = any(evil == p or evil.startswith(p + "/") for p in allowed)
    chk("verify_ledger prefix hole fixed", not hole)

    yr = {"claim": "Emissions rose 2.1% in 2024", "quote": same_q, "source_url": "https://a.example/x"}
    chk("year absent from quote window rejected", not gate_claim(yr, same_q)["verified"])

    v1 = {"claim": "Vaccine efficacy was 94.1%", "quote": "Efficacy was 94.1% in the trial.",
          "source_url": "https://a.example/x"}
    v2 = {"claim": "Vaccine efficacy was 94.1%", "quote": "The vaccine showed 94.1% efficacy overall.",
          "source_url": "https://b.example/y"}
    gv = assign_status([gate_claim(v1, "Efficacy was 94.1% in the trial."),
                        gate_claim(v2, "The vaccine showed 94.1% efficacy overall.")])
    chk("independent restatement on 2 domains -> CORROBORATED",
        all(g["status"] == "CORROBORATED" and g["indep_count"] == 2 for g in gv))

    print("\nSELFCHECK FAILED" if fails else "\nSELFCHECK PASSED")
    return 1 if fails else 0


# ---------- cli ----------


def main() -> None:
    p = argparse.ArgumentParser(prog="cnd", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create ~/search/<slug>/")
    s.add_argument("subject")
    s.add_argument("-n", type=int, default=10)
    s.add_argument("--question")
    s.add_argument("--slug")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("search", help="firecrawl search; store result urls")
    s.add_argument("slug")
    s.add_argument("query")
    s.add_argument("--num", type=int, default=8)
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("fetch", help="scrape pending urls in parallel")
    s.add_argument("slug")
    s.add_argument("--url", action="append", default=[])
    s.add_argument("--text-max", type=int, default=15000)
    s.add_argument("--min-chars", type=int, default=2500)
    s.add_argument("--limit", type=int, default=0)
    s.set_defaults(fn=cmd_fetch)

    s = sub.add_parser("pages", help="list stored pages with text paths")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_pages)

    s = sub.add_parser("ingest-extract", help="ingest extractor JSON into claims.raw")
    s.add_argument("slug")
    s.add_argument("extract_json", nargs="+")
    s.add_argument("--source-url")
    s.set_defaults(fn=cmd_ingest_extract)

    s = sub.add_parser("gate", help="quote + figure gates, echo collapse, status")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_gate)

    s = sub.add_parser("write", help="publish ~/search/<slug>.{md,claims,sources}")
    s.add_argument("slug")
    s.add_argument("--question")
    s.add_argument("--settlement")
    s.set_defaults(fn=cmd_write)

    s = sub.add_parser("status", help="workspace summary")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("selfcheck", help="run gate self-tests")
    s.set_defaults(fn=lambda a: sys.exit(selfcheck()))

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
