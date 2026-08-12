from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from . import firecrawl
from .gates import extract_ids, run_gates
from .merge import cluster_claims
from .util import (
    die,
    domain_of,
    dump_json,
    load_json,
    page_id_for_url,
    read_jsonl,
    utc_now,
    write_jsonl,
)
from .workspace import (
    ensure_layout,
    init_workspace,
    list_pages,
    list_sources,
    load_meta,
    page_paths,
    pub_paths,
    save_meta,
    upsert_source,
    work_dir,
)
from .write import publish, verify_ledger


def cmd_init(args: Any) -> None:
    meta = init_workspace(
        subject=args.subject,
        n=args.n,
        claim_class=args.claim_class,
        question=args.question,
        slug=args.slug,
    )
    wd = work_dir(meta["slug"])
    print(json.dumps({"ok": True, "slug": meta["slug"], "work_dir": str(wd), "meta": meta}, indent=2))


def cmd_search(args: Any) -> None:
    slug = args.slug
    load_meta(slug)
    ensure_layout(slug)
    channel = args.channel
    q = args.query
    num = args.num
    if not firecrawl.available():
        die("no FIRECRAWL_API_KEY set in ~/.agents/secrets/firecrawl.env")
    results = firecrawl.search(q, num_results=num)
    qrow = {
        "ts": utc_now(),
        "channel": channel,
        "query": q,
        "n_results": len(results),
        "urls": [r.get("url") for r in results if r.get("url")],
    }
    from .util import append_jsonl

    append_jsonl(work_dir(slug) / "queries.jsonl", qrow)

    for r in results:
        url = r.get("url")
        if not url:
            continue
        pid = page_id_for_url(url)
        pmeta = {
            "id": pid,
            "url": url,
            "title": r.get("title"),
            "domain": domain_of(url),
            "channel": channel,
            "class": args.source_class or "unknown",
            "publishedDate": r.get("publishedDate"),
            "text_len": 0,
            "from_search": True,
            "fetched": "no",
            "updated": utc_now(),
        }
        dump_json(page_paths(slug, url)["meta"], pmeta)
        upsert_source(
            slug,
            {
                "url": url,
                "title": pmeta.get("title"),
                "domain": pmeta.get("domain"),
                "class": pmeta.get("class"),
                "channel": pmeta.get("channel"),
                "date": pmeta.get("publishedDate"),
                "fetched": pmeta.get("fetched"),
                "page_id": pid,
            },
        )

    print(
        json.dumps(
            {
                "ok": True,
                "slug": slug,
                "query": q,
                "channel": channel,
                "results": len(results),
                "urls": qrow["urls"],
            },
            indent=2,
        )
    )


def _pdf_to_text(url: str, dest: Path) -> str | None:
    """Best-effort PDF extract via curl|pdftotext if available."""
    if not url.lower().endswith(".pdf"):
        return None
    if not shutil.which("pdftotext"):
        return None
    try:
        with tempfile.TemporaryDirectory() as td:
            pdf_path = Path(td) / "doc.pdf"
            subprocess.run(
                ["curl", "-fsSL", "--max-filesize", "200000000", "-o", str(pdf_path), url],
                check=True,
                timeout=120,
            )
            txt_path = Path(td) / "doc.txt"
            subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
                check=True,
                timeout=120,
            )
            text = txt_path.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                dest.write_text(text, encoding="utf-8")
                return text
    except Exception:
        return None
    return None


def cmd_fetch(args: Any) -> None:
    slug = args.slug
    load_meta(slug)
    ensure_layout(slug)
    urls: list[str] = []
    if args.url:
        urls = list(args.url)
    else:
        for s in list_sources(slug):
            u = s.get("url")
            if not u:
                continue
            paths = page_paths(slug, u)
            clen = 0
            if paths["txt"].exists():
                clen = len(paths["txt"].read_text(encoding="utf-8", errors="replace"))
            if clen < args.min_chars:
                urls.append(u)
        seen = set()
        urls = [u for u in urls if not (u in seen or seen.add(u))]
        if args.limit:
            urls = urls[: args.limit]

    if not urls:
        print(json.dumps({"ok": True, "fetched": 0, "note": "nothing to fetch"}))
        return

    if not firecrawl.available():
        die("no FIRECRAWL_API_KEY set in ~/.agents/secrets/firecrawl.env")
    try:
        results, statuses = firecrawl.contents(urls, text_max=args.text_max)
    except SystemExit:
        results, statuses = [], []
    got_urls = {r.get("url") for r in results}
    status_by_id = {s.get("id"): s for s in statuses}
    ok = fail = 0
    out_rows = []

    for r in results:
        url = r.get("url")
        if not url:
            continue
        text = r.get("text") or ""
        paths = page_paths(slug, url)
        pid = page_id_for_url(url)
        if (not text or len(text) < 2000) and url.lower().endswith(".pdf"):
            pdf_text = _pdf_to_text(url, paths["txt"])
            if pdf_text and len(pdf_text) > len(text):
                text = pdf_text
        if text:
            paths["txt"].write_text(text, encoding="utf-8")
            ok += 1
            fetched = "yes"
        else:
            fail += 1
            fetched = "no"
        pmeta = {
            "id": pid,
            "url": url,
            "title": r.get("title"),
            "domain": domain_of(url),
            "text_len": len(text),
            "fetched": fetched,
            "updated": utc_now(),
            "ids_mentioned": extract_ids(text[:80000]) if text else [],
        }
        if paths["meta"].exists():
            old = load_json(paths["meta"])
            pmeta = {**old, **pmeta}
        dump_json(paths["meta"], pmeta)
        upsert_source(
            slug,
            {
                "url": url,
                "title": pmeta.get("title") or r.get("title"),
                "domain": pmeta.get("domain"),
                "class": pmeta.get("class") or "unknown",
                "channel": pmeta.get("channel") or "warrant",
                "fetched": fetched,
                "page_id": pid,
                "text_len": len(text),
            },
        )
        out_rows.append({"url": url, "text_len": len(text), "fetched": fetched})

    for u in urls:
        if u not in got_urls:
            paths = page_paths(slug, u)
            pdf_text = _pdf_to_text(u, paths["txt"])
            if pdf_text:
                ok += 1
                dump_json(
                    paths["meta"],
                    {
                        **(load_json(paths["meta"]) if paths["meta"].exists() else {}),
                        "id": page_id_for_url(u),
                        "url": u,
                        "fetched": "yes",
                        "text_len": len(pdf_text),
                        "pdf_direct": True,
                        "updated": utc_now(),
                        "ids_mentioned": extract_ids(pdf_text[:80000]),
                    },
                )
                out_rows.append({"url": u, "text_len": len(pdf_text), "fetched": "yes"})
            else:
                fail += 1
                st = status_by_id.get(u) or {}
                out_rows.append({"url": u, "fetched": "no", "error": st})

    print(json.dumps({"ok": True, "slug": slug, "ok_n": ok, "fail_n": fail, "results": out_rows}, indent=2))


def cmd_pages(args: Any) -> None:
    pages = list_pages(args.slug)
    if args.json:
        print(json.dumps(pages, indent=2))
        return
    for p in pages:
        print(f"{p.get('text_len', 0):6d}  {p.get('channel', '?'):11}  {p.get('url', '')}")


def cmd_ingest_extract(args: Any) -> None:
    """Ingest extractor JSON file(s) into extracts/ and claims.raw.jsonl."""
    slug = args.slug
    load_meta(slug)
    ensure_layout(slug)
    paths_in = list(args.extract_json)
    raw_path = work_dir(slug) / "claims.raw.jsonl"
    existing = read_jsonl(raw_path)
    n_new = 0
    for path_s in paths_in:
        path = Path(path_s)
        if not path.exists():
            die(f"missing extract file: {path}")
        data = load_json(path)
        if isinstance(data, list):
            claims = data
            source_url = claims[0].get("source_url") if claims else None
            envelope = {
                "source_url": source_url,
                "source_class": args.source_class,
                "channel": args.channel,
                "fetch_ok": True,
                "claims": claims,
            }
        else:
            envelope = data
            claims = list(envelope.get("claims") or [])
        source_url = envelope.get("source_url") or args.source_url
        if not source_url:
            die(f"no source_url in {path}")
        pp = page_paths(slug, source_url)
        dump_json(pp["extract"], envelope)
        src_class = envelope.get("source_class") or args.source_class or "unknown"
        channel = envelope.get("channel") or args.channel or "warrant"
        for i, c in enumerate(claims):
            row = dict(c)
            row.setdefault("source_url", source_url)
            row.setdefault("source_class", src_class)
            row.setdefault("channel", channel)
            row.setdefault("claim_class", load_meta(slug).get("claim_class", "default"))
            row.setdefault("id", f"{page_id_for_url(source_url)}_{i}")
            existing.append(row)
            n_new += 1
    write_jsonl(raw_path, existing)
    print(json.dumps({"ok": True, "ingested_claims": n_new, "total_raw": len(existing)}))


def cmd_gate(args: Any) -> None:
    slug = args.slug
    load_meta(slug)
    wd = work_dir(slug)
    raw = read_jsonl(wd / "claims.raw.jsonl")
    if not raw:
        die("no claims.raw.jsonl — ingest extracts first")
    page_text = {}
    for s in list_sources(slug):
        u = s.get("url")
        if not u:
            continue
        pp = page_paths(slug, u)
        if pp["txt"].exists():
            page_text[u] = pp["txt"].read_text(encoding="utf-8", errors="replace")

    gated, stats = run_gates(raw, page_text)
    write_jsonl(wd / "claims.gated.jsonl", gated)
    print(
        json.dumps(
            {
                "ok": True,
                "gated": len(gated),
                "quote_ok": stats["quote_ok"],
                "quote_reject": stats["quote_reject"],
                "echo_groups": stats["echo_groups"],
                "independence_units": stats["independence_units"],
                "numeric_conflicts": stats["numeric_conflicts"],
            },
            indent=2,
        )
    )


def cmd_write(args: Any) -> None:
    slug = args.slug
    meta = load_meta(slug)
    wd = work_dir(slug)
    gated = read_jsonl(wd / "claims.gated.jsonl")
    clusters = read_jsonl(wd / "clusters.jsonl")
    if not clusters:
        clusters = cluster_claims(gated)
        write_jsonl(wd / "clusters.jsonl", clusters)
    if args.settlement:
        meta["settlement_criteria"] = args.settlement
        save_meta(slug, meta)
    if args.question:
        meta["question"] = args.question
        save_meta(slug, meta)
    paths = publish(slug, meta, gated, clusters)
    errs = verify_ledger(slug, gated)
    if errs:
        for p in paths.values():
            try:
                Path(p).unlink()
            except (OSError, TypeError):
                pass
        print(json.dumps({"ok": False, "verify_errors": errs, "action": "refused: fix urls before cnd write"}, indent=2))
        return
    print(json.dumps({"ok": True, "published": paths, "verify_errors": []}, indent=2))


def cmd_status(args: Any) -> None:
    slug = args.slug
    load_meta(slug)
    wd = work_dir(slug)
    print(
        json.dumps(
            {
                "slug": slug,
                "work_dir": str(wd),
                "sources": len(list_sources(slug)),
                "pages": len(list_pages(slug)),
                "raw_claims": len(read_jsonl(wd / "claims.raw.jsonl")),
                "gated_claims": len(read_jsonl(wd / "claims.gated.jsonl")),
                "clusters": len(read_jsonl(wd / "clusters.jsonl")),
                "published": {k: p.exists() for k, p in pub_paths(slug).items()},
            },
            indent=2,
        )
    )


def cmd_primary_probe(args: Any) -> None:
    """Scan pages for DOI/arxiv/NCT and print chase candidates."""
    slug = args.slug
    load_meta(slug)
    found = []
    for p in list_pages(slug):
        u = p.get("url")
        pp = page_paths(slug, u)
        if not pp["txt"].exists():
            continue
        text = pp["txt"].read_text(encoding="utf-8", errors="replace")[:80000]
        ids = extract_ids(text)
        if ids:
            found.append({"url": u, "ids": ids})
    print(json.dumps({"ok": True, "candidates": found}, indent=2))


def cmd_extract_stub(args: Any) -> None:
    """Print extract prompt + page path for agent to fill (no LLM in cnd)."""
    slug = args.slug
    url = args.url
    load_meta(slug)
    pp = page_paths(slug, url)
    if not pp["txt"].exists():
        die(f"no page text for {url}; run cnd fetch")
    prompt = (Path(__file__).resolve().parent.parent / "references" / "extract_prompt.md").read_text(
        encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "ok": True,
                "source_url": url,
                "page_text_path": str(pp["txt"]),
                "extract_out_path": str(pp["extract"]),
                "source_class": args.source_class or "unknown",
                "channel": args.channel or "warrant",
                "prompt_path": str(
                    Path(__file__).resolve().parent.parent / "references" / "extract_prompt.md"
                ),
                "instructions": "Read page_text_path, follow extract_prompt, write JSON to extract_out_path, then cnd ingest-extract",
            },
            indent=2,
        )
    )
