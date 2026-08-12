from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import (
    dump_json,
    load_json,
    page_id_for_url,
    parse_claim_class,
    read_jsonl,
    slugify,
    utc_now,
    write_jsonl,
)


def search_root() -> Path:
    return Path.home() / "search"


def work_dir(slug: str) -> Path:
    return search_root() / slug


def pub_paths(slug: str) -> dict[str, Path]:
    root = search_root()
    return {
        "md": root / f"{slug}.md",
        "claims": root / f"{slug}.claims.jsonl",
        "sources": root / f"{slug}.sources.jsonl",
    }


def ensure_layout(slug: str) -> Path:
    wd = work_dir(slug)
    for sub in ("pages", "extracts", "queries"):
        (wd / sub).mkdir(parents=True, exist_ok=True)
    return wd


def init_workspace(
    subject: str,
    n: int = 10,
    claim_class: str = "default",
    question: str | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    search_root().mkdir(parents=True, exist_ok=True)
    sl = slug or slugify(subject)
    wd = ensure_layout(sl)
    cc = parse_claim_class(claim_class)
    meta = {
        "slug": sl,
        "subject": subject,
        "question": question or subject,
        "settlement_criteria": "",
        "n": n,
        "claim_class": cc,
        "created": utc_now(),
        "updated": utc_now(),
    }
    dump_json(wd / "meta.json", meta)
    # touch empty ledgers
    for name in (
        "queries.jsonl",
        "sources.jsonl",
        "claims.raw.jsonl",
        "claims.gated.jsonl",
        "clusters.jsonl",
    ):
        p = wd / name
        if not p.exists():
            p.write_text("", encoding="utf-8")
    return meta


def load_meta(slug: str) -> dict[str, Any]:
    path = work_dir(slug) / "meta.json"
    if not path.exists():
        raise FileNotFoundError(f"no workspace for slug={slug} ({path})")
    return load_json(path)


def save_meta(slug: str, meta: dict[str, Any]) -> None:
    meta["updated"] = utc_now()
    dump_json(work_dir(slug) / "meta.json", meta)


def page_paths(slug: str, url: str) -> dict[str, Path | str]:
    wd = work_dir(slug)
    pid = page_id_for_url(url)
    return {
        "id": pid,
        "txt": wd / "pages" / f"{pid}.txt",
        "meta": wd / "pages" / f"{pid}.meta.json",
        "extract": wd / "extracts" / f"{pid}.json",
    }


def upsert_source(slug: str, row: dict[str, Any]) -> None:
    path = work_dir(slug) / "sources.jsonl"
    rows = read_jsonl(path)
    url = row.get("url")
    found = False
    for i, r in enumerate(rows):
        if r.get("url") == url:
            rows[i] = {**r, **row}
            found = True
            break
    if not found:
        rows.append(row)
    write_jsonl(path, rows)


def list_sources(slug: str) -> list[dict[str, Any]]:
    return read_jsonl(work_dir(slug) / "sources.jsonl")


def list_pages(slug: str) -> list[dict[str, Any]]:
    wd = work_dir(slug) / "pages"
    out = []
    if not wd.exists():
        return out
    for meta_path in sorted(wd.glob("*.meta.json")):
        try:
            out.append(load_json(meta_path))
        except Exception:
            continue
    return out
