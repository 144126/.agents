import argparse
import json
import sys

from . import __version__, FORMAT_VERSION
from .dsl import parse_graph, serialize_graph
from .errors import AtgError, EXIT_OK, EXIT_USAGE
from . import selftest


def build_parser():
    parser = argparse.ArgumentParser(prog="atg", description="Atomic Task Graph engine")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="print version")

    test_cmd = sub.add_parser("selftest", help="run the built-in test suite")
    test_cmd.add_argument("-v", "--verbose", action="store_true")

    fmt_cmd = sub.add_parser("fmt", help="canonicalize a .atg file")
    fmt_cmd.add_argument("file")
    fmt_cmd.add_argument("-w", "--write", action="store_true", help="rewrite in place")

    return parser


def cmd_version(args):
    if args.json:
        print(json.dumps({"version": __version__, "format": FORMAT_VERSION}))
    else:
        print("atg %s (format atg/%d)" % (__version__, FORMAT_VERSION))
    return EXIT_OK


def cmd_selftest(args):
    return selftest.run(verbose=args.verbose)


def cmd_fmt(args):
    with open(args.file, "r") as handle:
        text = handle.read()
    out = serialize_graph(parse_graph(text, args.file))
    if args.write:
        if out != text:
            with open(args.file, "w") as handle:
                handle.write(out)
        print("%s: %s" % (args.file, "rewritten" if out != text else "already canonical"))
    else:
        sys.stdout.write(out)
    return EXIT_OK


COMMANDS = {"version": cmd_version, "selftest": cmd_selftest, "fmt": cmd_fmt}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE
    try:
        return COMMANDS[args.command](args)
    except AtgError as err:
        if args.json:
            print(json.dumps({"ok": False, "error": err.as_dict()}))
        else:
            sys.stderr.write(str(err) + "\n")
        return err.exit_code
    except (IOError, OSError) as err:
        sys.stderr.write("E_IO: %s\n" % err)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
