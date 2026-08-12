#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow running as python -m cnd.cli from skill root or via bin/cnd
_SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

from cnd import commands  # noqa: E402
from cnd import gates_selfcheck as commands_selfcheck  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cnd",
        description="Condense runner: disk-backed search → fetch → extract → gate → ledger",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create ~/search/<slug>/ workspace")
    s.add_argument("subject", help="topic / subject string")
    s.add_argument("-n", type=int, default=10, help="source budget (default 10)")
    s.add_argument(
        "--claim-class",
        default="default",
        choices=["default", "spec", "efficacy", "lived"],
    )
    s.add_argument("--question", default=None)
    s.add_argument("--slug", default=None)
    s.set_defaults(func=commands.cmd_init)

    s = sub.add_parser("search", help="firecrawl search; store urls under pages/")
    s.add_argument("slug")
    s.add_argument("query")
    s.add_argument(
        "--channel",
        default="warrant",
        choices=["warrant", "outside", "adversarial"],
    )
    s.add_argument("--num", type=int, default=8)
    s.add_argument("--text-max", type=int, default=8000)
    s.add_argument("--source-class", default="unknown")
    s.set_defaults(func=commands.cmd_search)

    s = sub.add_parser("fetch", help="bulk firecrawl scrape for pending urls")
    s.add_argument("slug")
    s.add_argument("--url", action="append", default=[])
    s.add_argument("--text-max", type=int, default=15000)
    s.add_argument("--min-chars", type=int, default=2500)
    s.add_argument("--limit", type=int, default=0)
    s.set_defaults(func=commands.cmd_fetch)

    s = sub.add_parser("pages", help="list stored pages")
    s.add_argument("slug")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=commands.cmd_pages)

    s = sub.add_parser(
        "extract-stub",
        help="print paths/prompt for agent extraction of one url",
    )
    s.add_argument("slug")
    s.add_argument("url")
    s.add_argument("--class", dest="source_class", default="unknown")
    s.add_argument(
        "--channel",
        default="warrant",
        choices=["warrant", "outside", "adversarial"],
    )
    s.set_defaults(func=commands.cmd_extract_stub)

    s = sub.add_parser("ingest-extract", help="ingest extractor JSON into claims.raw")
    s.add_argument("slug")
    s.add_argument("extract_json", nargs="+")
    s.add_argument("--source-url", default=None)
    s.add_argument("--class", dest="source_class", default=None)
    s.add_argument(
        "--channel",
        default=None,
        choices=["warrant", "outside", "adversarial"],
    )
    s.set_defaults(func=commands.cmd_ingest_extract)

    s = sub.add_parser("gate", help="quote + echo + numeric gates → claims.gated")
    s.add_argument("slug")
    s.set_defaults(func=commands.cmd_gate)

    s = sub.add_parser("write", help="publish ~/search/<slug>.{md,claims,sources}")
    s.add_argument("slug")
    s.add_argument("--question", default=None)
    s.add_argument("--settlement", default=None)
    s.set_defaults(func=commands.cmd_write)

    s = sub.add_parser("status", help="workspace summary")
    s.add_argument("slug")
    s.set_defaults(func=commands.cmd_status)

    s = sub.add_parser("primary-probe", help="list DOI/arxiv/NCT ids in pages")
    s.add_argument("slug")
    s.set_defaults(func=commands.cmd_primary_probe)

    s = sub.add_parser("selfcheck", help="run gate self-tests")
    s.set_defaults(func=lambda a: _raise(commands_selfcheck.main()))

    return p


def _raise(code: int) -> None:
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
