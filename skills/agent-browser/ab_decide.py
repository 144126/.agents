#!/usr/bin/env python3
"""Closed-menu agent-browser loop. Julia picks; this file runs the CLI."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

JULIA_ROOT = os.path.expanduser("~/models/julia-1")
PYTHON = os.path.expanduser("~/work/decision-julia/.venv/bin/python")
CDP = "9223"
MAX_TARGETS = 8
CHROME = (
    "jump to content",
    "main menu",
    "skip to",
    "privacy policy",
    "terms of use",
    "cookie",
    "wikimedia",
    "download wikipedia",
    "other projects",
    "languages",
    "namespaces",
)


def ensure_cdp():
    try:
        urllib.request.urlopen("http://127.0.0.1:9223/json/version", timeout=1).read()
        return
    except Exception:
        pass
    subprocess.run(["ab-1440fl", "get", "url"], check=False, capture_output=True)
    urllib.request.urlopen("http://127.0.0.1:9223/json/version", timeout=3).read()


def ab(session, args, json_out=True):
    cmd = [
        "agent-browser",
        "--session",
        session,
        "--cdp",
        CDP,
        "--pin-tab",
        "--headed",
        "false",
        "--auto-connect",
        "false",
        "--idle-timeout",
        "15m",
    ]
    if json_out:
        cmd.append("--json")
    cmd.extend(args)
    p = subprocess.run(cmd, capture_output=True, text=True)
    text = p.stdout if p.stdout else p.stderr
    data = None
    if json_out:
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            data = {"success": False, "error": text[-400:], "raw": p.stdout}
    return p.returncode, data, text


def payload(data, key, default=None):
    if not isinstance(data, dict):
        return default
    inner = data.get("data")
    if isinstance(inner, dict) and key in inner:
        return inner[key]
    return data.get(key, default)


def tokens(text):
    return set(re.findall(r"[a-z0-9]{2,}", (text or "").lower()))


def chrome_name(name):
    n = (name or "").lower()
    return any(n == c or n.startswith(c) for c in CHROME)


def shortlist(refs, goal, limit=MAX_TARGETS):
    goal_t = tokens(goal)
    fields, scored = [], []
    for eid, meta in refs.items():
        if not re.fullmatch(r"e\d+", eid):
            continue
        role = (meta or {}).get("role") or ""
        name = (meta or {}).get("name") or ""
        if role in ("textbox", "searchbox", "spinbutton"):
            kind = "type"
        elif role in ("link", "button", "checkbox", "radio", "tab", "menuitem", "option", "switch", "combobox"):
            kind = "click"
        else:
            continue
        if chrome_name(name):
            continue
        label = f"{role} {name}".strip()[:80]
        overlap = len(goal_t & tokens(label))
        if kind == "type" and "search" in label.lower():
            overlap += 4
        row = (overlap, kind, eid, label)
        (fields if kind == "type" else scored).append(row)
    scored.sort(key=lambda row: (-row[0], row[2]))
    keep = fields[:3] + scored[: max(0, limit - len(fields[:3]))]
    return keep, max(0, len(fields) + len(scored) - len(keep))


def confidence(probs):
    vals = list(probs.values())
    n = len(vals)
    if n < 2:
        return max(vals) if vals else 0.0
    return (max(vals) - 1 / n) / (1 - 1 / n)


class Julia:
    def __init__(self):
        if JULIA_ROOT not in sys.path:
            sys.path.insert(0, JULIA_ROOT)
        from julia import load_model

        self.engine = load_model(
            JULIA_ROOT,
            device="cpu",
            strict_encoding=True,
            max_length=1024,
            head_length=256,
        )

    def pick(self, state, questions):
        t0 = time.perf_counter()
        result = self.engine.predict(state=state, questions=questions)
        return result["answers"], (time.perf_counter() - t0) * 1000


def decide(engine, goal, url, title, menu, history, omitted=0):
    clicks = {eid: label for kind, eid, label in ((r[1], r[2], r[3]) for r in menu) if kind == "click"}
    types = {eid: label for kind, eid, label in ((r[1], r[2], r[3]) for r in menu) if kind == "type"}
    ops = {"done": "Visible evidence already satisfies every part of the goal"}
    if clicks:
        ops["click"] = "Activate a visible control that advances the goal"
    if types:
        ops["type"] = "Type into an empty field required by the goal"
    if omitted and not types:
        ops["scroll"] = "The needed control is offscreen"
    questions = {
        "op": {
            "type": "choice",
            "instructions": f"Which next browser operation advances this goal: {goal}",
            "criteria": ops,
        }
    }
    if clicks:
        criteria = {eid: label for eid, label in clicks.items()}
        criteria["none"] = "Do not click"
        questions["click_target"] = {
            "type": "choice",
            "instructions": f"If clicking, which control advances this goal: {goal}",
            "criteria": criteria,
        }
    if types:
        criteria = {eid: label for eid, label in types.items()}
        criteria["none"] = "Do not type"
        questions["type_target"] = {
            "type": "choice",
            "instructions": f"If typing, which field should receive text for this goal: {goal}",
            "criteria": criteria,
        }
    state = {
        "goal": goal,
        "url": url,
        "title": title,
        "elements": [{"id": eid, "kind": kind, "label": label} for kind, eid, label in ((r[1], r[2], r[3]) for r in menu)],
        "history": history[-8:],
    }
    answers, ms = engine.pick(state, questions)
    op = answers["op"]["choice"]
    target = None
    if op == "click" and "click_target" in answers:
        target = answers["click_target"]["choice"]
        if target == "none":
            op = "done"
            target = None
    elif op == "type" and "type_target" in answers:
        target = answers["type_target"]["choice"]
        if target == "none":
            op = "done"
            target = None
    return {
        "op": op,
        "target": target,
        "ms": ms,
        "op_p": answers["op"]["probabilities"],
        "op_conf": confidence(answers["op"]["probabilities"]),
        "target_p": answers.get("click_target" if op == "click" else "type_target", {}).get("probabilities"),
    }


def run(goal, url, session, max_steps, dry, text):
    ensure_cdp()
    engine = Julia()
    rc, _, err = ab(session, ["open", url], json_out=False)
    if rc != 0 and "tab_gone" in (err or ""):
        ab(session, ["tab", "new", url], json_out=False)
        rc, _, err = ab(session, ["open", url], json_out=False)
    if rc != 0:
        raise SystemExit(f"open failed: {err[-300:] if err else rc}")
    host = url.split("//", 1)[-1].split("/", 1)[0]
    ab(session, ["wait", "--url", f"**{host}**"], json_out=False)
    history = []
    last_url = ""
    for step in range(1, max_steps + 1):
        _, u, _ = ab(session, ["get", "url"])
        _, t, _ = ab(session, ["get", "title"])
        _, snap, _ = ab(session, ["snapshot", "-i"])
        page_url = payload(u, "url") or ""
        title = payload(t, "title") or ""
        refs = payload(snap, "refs") or {}
        menu, omitted = shortlist(refs, goal)
        rec = {
            "step": step,
            "url": page_url,
            "title": title,
            "n_refs": len(refs),
            "n_menu": len(menu),
            "omitted": omitted,
        }
        goal_hits = tokens(goal) & (tokens(page_url) | tokens(title))
        if step > 1 and len(goal_hits) >= 1 and page_url != url:
            rec["status"] = "url_match"
            rec["goal_hits"] = sorted(goal_hits)
            print(json.dumps(rec))
            break
        if not menu and step == 1:
            rec["status"] = "empty_menu"
            print(json.dumps(rec))
            break
        pick = decide(engine, goal, page_url, title, menu, history, omitted)
        if text and any(r[1] == "type" for r in menu) and "type" not in " ".join(history):
            field = next(r[2] for r in menu if r[1] == "type")
            pick = {**pick, "op": "type", "target": field, "forced": "search_field"}
        rec.update(pick)
        if dry:
            rec["status"] = "dry"
            print(json.dumps(rec))
            break
        if pick["op"] == "done" or pick["op_conf"] < 0.2:
            rec["status"] = "done" if pick["op"] == "done" else "low_confidence"
            print(json.dumps(rec))
            break
        if pick["op"] == "wait":
            ab(session, ["wait", "--load", "load"], json_out=False)
            history.append("wait")
            rec["status"] = "waited"
            print(json.dumps(rec))
            continue
        if pick["op"] == "scroll":
            ab(session, ["scroll", "down", "600"], json_out=False)
            history.append("scroll")
            rec["status"] = "scrolled"
            print(json.dumps(rec))
            continue
        if pick["op"] in ("click", "type") and pick["target"] and pick["target"] in {r[2] for r in menu}:
            ref = "@" + pick["target"]
            if pick["op"] == "click":
                rc, _, err = ab(session, ["click", ref], json_out=False)
                history.append(f"click {pick['target']}")
            else:
                if not text:
                    rec["status"] = "need_text"
                    print(json.dumps(rec))
                    break
                rc, _, err = ab(session, ["fill", ref, text], json_out=False)
                if rc == 0:
                    ab(session, ["press", "Enter"], json_out=False)
                    slug = re.sub(r"[^a-z0-9]+", "", text.lower())
                    if slug:
                        ab(session, ["wait", "--url", f"**{slug}**"], json_out=False)
                history.append(f"type {pick['target']}")
            if rc != 0:
                rec["status"] = "act_failed"
                rec["error"] = (err or "")[-200:]
                print(json.dumps(rec))
                break
            ab(session, ["wait", "--load", "domcontentloaded"], json_out=False)
            rec["status"] = "acted"
            print(json.dumps(rec))
            last_url = page_url
            continue
        rec["status"] = "blocked"
        print(json.dumps(rec))
        break
    _, u, _ = ab(session, ["get", "url"])
    return payload(u, "url") or last_url


def main():
    p = argparse.ArgumentParser(description="Julia-driven agent-browser loop")
    p.add_argument("--goal", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--session", default="ab-decide")
    p.add_argument("--max-steps", type=int, default=6)
    p.add_argument("--dry", action="store_true")
    p.add_argument("--text", default="")
    args = p.parse_args()
    if sys.executable != PYTHON and os.path.isfile(PYTHON):
        os.execv(PYTHON, [PYTHON, __file__, *sys.argv[1:]])
    final = run(args.goal, args.url, args.session, args.max_steps, args.dry, args.text)
    print(json.dumps({"final_url": final}))


if __name__ == "__main__":
    main()
