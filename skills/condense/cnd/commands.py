from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .gates import gate_quote
from .util import (
    die,
    load_json,
    norm_ws,
    write_jsonl,
)


def _read_source(args: Any) -> str:
    if getattr(args, "file", None):
        p = Path(args.file)
    elif getattr(args, "source", None):
        p = Path(args.source)
    else:
        p = None
    if p is not None:
        if not p.exists():
            die(f"no source file: {p}")
        return p.read_text(encoding="utf-8", errors="replace")
    if getattr(args, "text", None) is not None:
        return args.text
    die("provide --source <file> or --text")


def _load_claims(path: str) -> list[dict[str, Any]]:
    data = load_json(Path(path))
    if isinstance(data, list):
        return data
    return list(data.get("claims") or [])


def cmd_extract(args: Any) -> None:
    text = _read_source(args)
    prompt = Path(__file__).resolve().parent / "references" / "extract_prompt.md"
    print(json.dumps({
        "ok": True,
        "prompt_path": str(prompt),
        "source_chars": len(text),
        "instructions": (
            "Follow references/extract_prompt.md. Draw every quote verbatim from "
            "the source text. Write the claims to a JSON file (envelope or list), "
            "then run: condense gate --source <file> --claims <json>"
        ),
    }, indent=2))


def _is_fact(c: dict[str, Any]) -> bool:
    return bool(c.get("quote_found")) and not c.get("number_gate_fail") and not c.get("polarity_fail")


def _render_facts(gated: list[dict[str, Any]]) -> str:
    facts = [c for c in gated if _is_fact(c)]
    warns = [c for c in gated if not _is_fact(c)]
    lines = ["# Condensed facts", ""]
    if facts:
        lines.append(f"{len(facts)} fact(s), each quote-anchored to the source text.")
        lines.append("")
        for c in facts:
            q = c.get("quote") or ""
            lines.append(f"> {c.get('claim', '').strip()} — \"{norm_ws(q)}\"")
        lines.append("")
    else:
        lines.append("No quote-anchored facts extracted.")
        lines.append("")
    if warns:
        lines.append("## Rejected (quote not found verbatim in source)")
        lines.append("")
        for c in warns:
            reasons = ", ".join(c.get("gate_reasons") or ["quote_fail"])
            lines.append(f"- {c.get('claim', '').strip()} — {reasons}")
        lines.append("")
    return "\n".join(lines)


def cmd_gate(args: Any) -> None:
    text = _read_source(args)
    claims = _load_claims(args.claims)
    if not claims:
        die("no claims in --claims file")
    gated = [gate_quote(c, text) for c in claims]
    if args.jsonl:
        write_jsonl(Path(args.jsonl), gated)
    md = _render_facts(gated)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(json.dumps({
            "ok": True,
            "facts": sum(1 for c in gated if _is_fact(c)),
            "rejected": sum(1 for c in gated if not _is_fact(c)),
            "out": args.out,
        }, indent=2))
    else:
        print(md)


def selfcheck() -> int:
    from . import gates_selfcheck

    return gates_selfcheck.main()
