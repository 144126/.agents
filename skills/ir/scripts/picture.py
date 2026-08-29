#!/usr/bin/env python3
"""render SVG; generate/edit via Muse Spark Image. 3-call ceiling."""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "meta/muse-spark-1.2"
API = "https://openrouter.ai/api/v1/chat/completions"
MAX = 3
STATE = ".picture-draft-state.json"


def load(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {"calls": 0, "history": []}


def save(p: Path, s: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, indent=2))


def render(svg: str, png: str) -> None:
    out = Path(png)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "inkscape",
            svg,
            "--export-type=png",
            f"--export-filename={out}",
            "--export-width=1024",
            "--export-height=1024",
        ],
        check=True,
    )
    print(out)


def key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        sys.exit("export OPENROUTER_API_KEY=sk-or-v1-...")
    return k


def b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def post(prompt: str, images: list[str]) -> dict:
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in images:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(p)}"}}
        )
    req = urllib.request.Request(
        API,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": content}],
                "modalities": ["image", "text"],
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def save_image(resp: dict, out: str) -> None:
    msg = resp["choices"][0]["message"]
    urls: list[str] = []
    for img in msg.get("images") or []:
        urls.append((img.get("image_url") or img).get("url") or img.get("url") or "")
    if isinstance(msg.get("content"), list):
        for part in msg["content"]:
            if part.get("type") == "image_url":
                urls.append(part["image_url"]["url"])
    url = next(u for u in urls if u)
    data = (
        base64.b64decode(url.split(",", 1)[1])
        if url.startswith("data:")
        else urllib.request.urlopen(url, timeout=60).read()
    )
    Path(out).write_bytes(data)
    print(out)


def muse(mode: str, prompt: str, out: str, refs: list[str]) -> None:
    for p in refs:
        if not Path(p).exists():
            sys.exit(f"missing {p}")
    sp = Path(out).parent / STATE
    s = load(sp)
    if s["calls"] >= MAX:
        sys.exit(f"{s['calls']}/{MAX} used — stop")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = post(prompt, refs)
        save_image(resp, out)
    except urllib.error.HTTPError as e:
        sys.exit(f"{e.code} {e.read().decode()[:500]}")
    s["calls"] += 1
    s["history"].append({"mode": mode, "out": out, "ts": int(time.time())})
    save(sp, s)
    print(f"{s['calls']}/{MAX}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="c", required=True)
    r = sub.add_parser("render")
    r.add_argument("svg")
    r.add_argument("png")
    g = sub.add_parser("generate")
    g.add_argument("--prompt", required=True)
    g.add_argument("--ref", required=True)
    g.add_argument("--out", required=True)
    e = sub.add_parser("edit")
    e.add_argument("--image", required=True)
    e.add_argument("--prompt", required=True)
    e.add_argument("--out", required=True)
    st = sub.add_parser("status")
    st.add_argument("--dir", default=".")
    a = p.parse_args()
    if a.c == "render":
        render(a.svg, a.png)
    elif a.c == "generate":
        muse("generate", a.prompt, a.out, [a.ref])
    elif a.c == "edit":
        muse("edit", a.prompt, a.out, [a.image])
    else:
        print(json.dumps(load(Path(a.dir) / STATE), indent=2))


if __name__ == "__main__":
    main()
