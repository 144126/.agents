from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .util import die

DEFAULT_API = "https://api.firecrawl.dev/v1"
SECRETS_ENV = Path.home() / ".agents" / "secrets" / "firecrawl.env"


def load_api_key() -> str:
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if key:
        return key
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("FIRECRAWL_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
                if key:
                    os.environ["FIRECRAWL_API_KEY"] = key
                    return key
    return ""


def available() -> bool:
    return bool(load_api_key())


def _post(path: str, body: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    key = load_api_key()
    if not key:
        die("no FIRECRAWL_API_KEY (set env or ~/.agents/secrets/firecrawl.env)")
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{DEFAULT_API}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        die(f"firecrawl HTTP {e.code} on {path}: {err[:500]}")
    except urllib.error.URLError as e:
        die(f"firecrawl network error on {path}: {e}")
    return {}


def search(
    query: str,
    *,
    num_results: int = 8,
) -> list[dict[str, Any]]:
    """URL/title discovery only. Full page text is fetched with contents()."""
    limit = max(1, min(num_results, 20))
    body = {
        "query": query,
        "limit": limit,
        "timeout": 60000,
    }
    data = _post("/search", body)
    out = []
    for r in data.get("data") or []:
        out.append(
            {
                "url": r.get("url"),
                "title": r.get("title") or r.get("metadata", {}).get("title"),
                "text": "",
                "publishedDate": r.get("publishedDate")
                or r.get("metadata", {}).get("publishedTime"),
                "backend": "firecrawl",
            }
        )
    return out


def contents(
    urls: list[str],
    *,
    text_max: int = 15000,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Live scrape of current page text (no cache)."""
    if not urls:
        return [], []
    results = []
    statuses = []
    for u in urls:
        body = {
            "url": u,
            "formats": ["markdown"],
            "timeout": 60000,
        }
        try:
            data = _post("/scrape", body, timeout=120)
        except SystemExit:
            statuses.append({"id": u, "status": "error", "note": "request failed"})
            continue
        doc = data.get("data") or {}
        text = (doc.get("markdown") or "")[:text_max]
        results.append({"url": u, "text": text})
        statuses.append(
            {"id": u, "status": "ok" if text else "empty"}
        )
    return results, statuses
