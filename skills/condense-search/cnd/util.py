from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


def die(msg: str, code: int = 1) -> None:
    print(f"cnd: {msg}", file=sys.stderr)
    raise SystemExit(code)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify(text: str, max_len: int = 64) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "topic")[:max_len].strip("-")


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()


def page_id_for_url(url: str) -> str:
    return sha1_text(normalize_url(url))[:16]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(url: str) -> str:
    host = domain_of(url)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) < 2:
        return host
    # handle multi-label TLDs so ccTLD webs don't collapse to ".uk" etc.
    two_label_tlds = {
        "co.uk", "org.uk", "ac.uk", "gov.uk", "me.uk", "ltd.uk", "net.uk",
        "com.au", "net.au", "org.au", "edu.au", "gov.au", "asn.au",
        "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp",
        "co.nz", "ac.nz", "govt.nz", "geek.nz",
        "co.za", "org.za", "gov.za",
        "co.in", "net.in", "org.in", "gov.in",
        "com.br", "org.br", "gov.br", "net.br",
        "co.il", "org.il", "gov.il",
    }
    if len(parts) >= 3 and ".".join(parts[-2:]) in two_label_tlds:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def norm_quote_key(s: str) -> str:
    s = norm_ws(s).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def normalize_url(url: str) -> str:
    """Canonical key for dedupe: drop scheme, www, trailing slash, fragments."""
    try:
        p = urlparse(url.strip())
    except Exception:
        return url.strip().lower()
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (p.path or "").rstrip("/")
    q = p.query or ""
    # drop tracking params that vary per result but not per page
    skip = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}
    if q:
        parts = []
        for kv in q.split("&"):
            k = kv.split("=", 1)[0].lower()
            if k and k not in skip:
                parts.append(kv)
        q = "&".join(sorted(parts))
    return f"{host}{path}{('?' + q) if q else ''}"


CLAIM_CLASS_ALIASES = {
    "spec": "spec",
    "law": "spec",
    "api": "spec",
    "statute": "spec",
    "efficacy": "efficacy",
    "causation": "efficacy",
    "controversy": "efficacy",
    "lived": "lived",
    "operator": "lived",
    "failure": "lived",
    "default": "default",
    "mixed": "default",
}


def parse_claim_class(raw: str | None) -> str:
    if not raw:
        return "default"
    key = raw.strip().lower()
    return CLAIM_CLASS_ALIASES.get(key, "default")
