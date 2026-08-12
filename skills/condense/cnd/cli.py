#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from cnd import commands  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="condense",
        description="Condense a single text block or file into quote-anchored facts.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract", help="print the extract prompt for a text block")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="path to a text file to condense")
    g.add_argument("--text", help="inline text block to condense")
    s.set_defaults(func=commands.cmd_extract)

    s = sub.add_parser("gate", help="gate extracted claims against the source text")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--source", help="path to the source text file")
    src.add_argument("--text", help="inline source text")
    s.add_argument("--claims", required=True, help="extracted claims JSON (envelope or list)")
    s.add_argument("--jsonl", default=None, help="write gated claims to this path")
    s.add_argument("--out", default=None, help="write facts markdown to this path (else stdout)")
    s.set_defaults(func=commands.cmd_gate)

    s = sub.add_parser("selfcheck", help="run gate self-tests")
    s.set_defaults(func=lambda a: _raise(commands.selfcheck()))

    return p


def _raise(code: int) -> None:
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
