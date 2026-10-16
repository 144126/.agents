#!/usr/bin/env python3
"""sift — the agent finds pages, sift fetches them, local julia judges, prints the urls worth reading."""
import argparse
import html
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

JULIA_DIR = Path(os.environ.get("JULIA_DIR", Path.home() / "models" / "julia-1"))
PY_CANDIDATES = [
    os.environ.get("JULIA_PYTHON", ""),
    str(Path.home() / "work/decision-julia/.venv-julia/bin/python"),
    str(JULIA_DIR / ".venv/bin/python"),
]


def die(msg, code=1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def reexec_with_julia():
    here = str(JULIA_DIR)
    path = os.environ.get("PYTHONPATH", "")
    if here not in path.split(os.pathsep):
        os.environ["PYTHONPATH"] = here + (os.pathsep + path if path else "")
    try:
        import torch  # noqa: F401
        from julia import load_model  # noqa: F401
        return
    except Exception:
        pass
    for py in PY_CANDIDATES:
        if py and Path(py).is_file() and not os.path.samefile(py, sys.executable):
            os.execv(py, [py, str(Path(__file__).resolve()), *sys.argv[1:]])
    die("julia python not found. set JULIA_PYTHON to the venv that has torch + julia")


reexec_with_julia()

from julia import load_model  # noqa: E402

QS = {
    "relevant": {
        "instructions": "Does `text` help answer `research`?",
        "criteria": {
            "false": "Off-topic, empty, or no usable information about `research`.",
            "true": "The page addresses `research` with usable information.",
        },
    },
    "read": {
        "instructions": "Must a researcher read this page, or is knowing it is relevant enough?",
        "criteria": {
            "false": "Knowing the page is relevant already captures what it offers.",
            "true": "The page has facts, numbers, quotes, or nuance worth reading in full.",
        },
    },
    "primary": {
        "instructions": "Is this a primary source for `research`?",
        "criteria": {
            "false": "Recap, SEO page, forum take, or secondary summary.",
            "true": "Official docs, paper, spec, dataset, or original statement.",
        },
    },
    "usable": {
        "instructions": "Does the page state a concrete fact, figure, or claim that could be cited?",
        "criteria": {
            "false": "Vague, empty, or only opinion without a checkable claim.",
            "true": "States a concrete fact, figure, or checkable claim.",
        },
    },
}

THIN = 250
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.title, self.skip, self.in_title = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header"):
            self.skip += 1
        self.in_title = tag == "title"

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header") and self.skip:
            self.skip -= 1
        self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif not self.skip:
            self.parts.append(data)


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain,*/*"})
        with urllib.request.urlopen(req, timeout=25) as r:
            if "html" not in r.headers.get("Content-Type", "html") and "text" not in r.headers.get("Content-Type", ""):
                return {"url": url, "title": "", "text": ""}
            raw = r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except Exception as e:
        print(f"  ! {url}: {str(e)[:120]}", file=sys.stderr)
        return {"url": url, "title": "", "text": ""}
    p = Text()
    try:
        p.feed(raw)
    except Exception:
        pass
    return {"url": url, "title": p.title.strip(), "text": re.sub(r"\s+", " ", html.unescape(" ".join(p.parts))).strip()}


def softmax(z):
    m = max(z)
    p = [pow(2.718281828459045, x - m) for x in z]
    t = sum(p) or 1.0
    return [x / t for x in p]


def judge(engine, research, pages):
    rows = []
    for pg in pages:
        state = {"research": research, "url": pg["url"], "title": pg["title"], "text": pg["text"][:8000]}
        rows += [
            {"state": state, "question": q["instructions"], "type": "noul", "options": [q["criteria"]["false"], q["criteria"]["true"]]}
            for q in QS.values()
        ]
    t0 = time.time()
    scores = engine.logits(rows)
    print(f"julia {len(pages)} pages / {len(rows)} q  {time.time() - t0:.1f}s", file=sys.stderr)
    n = len(QS)
    return [
        {k: softmax(z)[1] for k, z in zip(QS, scores[i * n:(i + 1) * n])}
        for i in range(len(pages))
    ]


def keep(pg, j):
    if len(pg["text"]) < THIN:
        return False
    return j["relevant"] >= 0.45 and (j["read"] >= 0.55 or (j["usable"] >= 0.7 and j["read"] >= 0.4))


def main():
    ap = argparse.ArgumentParser(description="Judge pages with local julia; print the urls worth reading.")
    ap.add_argument("question")
    ap.add_argument("urls", nargs="*", help="urls to judge; read from stdin, one per line, when none given")
    ap.add_argument("--max", type=int, default=0, help="print at most N urls")
    ap.add_argument("--scores", action="store_true", help="print julia scores next to each url")
    a = ap.parse_args()
    urls = list(dict.fromkeys(u.strip() for u in (a.urls or sys.stdin.read().split()) if u.strip().startswith("http")))
    if not urls:
        die("no urls. usage: sift \"<question>\" URL... (or urls on stdin)")
    with ThreadPoolExecutor(12) as ex:
        pages = list(ex.map(fetch, urls))
    live = [p for p in pages if len(p["text"]) >= THIN]
    print(f"fetched {len(live)}/{len(urls)} pages with text", file=sys.stderr)
    if not live:
        return
    print("loading julia-1…", file=sys.stderr)
    engine = load_model(
        str(JULIA_DIR),
        device="cpu",
        max_length=int(os.environ.get("SIFT_JULIA_LEN", "2048")),
        head_length=384,
        batch_size=8,
        strict_encoding=False,
    )
    ranked = sorted(
        ((pg, j) for pg, j in zip(live, judge(engine, a.question, live)) if keep(pg, j)),
        key=lambda x: -(x[1]["relevant"] + x[1]["read"] + x[1]["usable"] + 0.5 * x[1]["primary"]),
    )
    print(f"kept {len(ranked)}/{len(urls)}", file=sys.stderr)
    for pg, j in ranked[: a.max or None]:
        print(pg["url"] + ("\t" + " ".join(f"{k}={v:.2f}" for k, v in j.items()) if a.scores else ""))


if __name__ == "__main__":
    main()
