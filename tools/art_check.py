"""Syntax-check an ART script and report problems as JSON.

Runs the lexer and parser only - never the interpreter - so it is safe to
call on every keystroke from an editor. Output on stdout is always a
single JSON object:

    {"diagnostics": [{"line": 3, "column": 12, "message": "...",
                      "stage": "Parse error", "severity": "error"}]}

Usage:
    python3 tools/art_check.py path/to/script.art
    python3 tools/art_check.py --stdin
    python3 art_check.py --root /path/to/art-language --stdin

`--stdin` reads the source from standard input, which is what editors
want for an unsaved buffer. `--root` points at the interpreter checkout
to import `art` from, for copies of this script that live outside it
(the VS Code extension ships one).
"""
import json
import os
import sys


def _take_root(argv):
    """Pop a leading `--root DIR` off argv, returning the directory to
    import the `art` package from."""
    if len(argv) >= 3 and argv[1] == "--root":
        root = argv[2]
        del argv[1:3]
        return root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


sys.path.insert(0, _take_root(sys.argv))

from art.lexer import Lexer  # noqa: E402
from art.parser import Parser  # noqa: E402
from art.errors import ArtError  # noqa: E402


def check(source):
    """Return a list of diagnostic dicts for `source`.

    The pipeline raises on the first problem it hits, so this is either
    empty or a single diagnostic.
    """
    try:
        Parser(Lexer(source).tokenize()).parse()
    except ArtError as error:
        return [{
            "line": error.line or 1,
            "column": error.column or 1,
            "message": error.message,
            "stage": error.stage,
            "severity": "error",
        }]
    except RecursionError:
        return [{
            "line": 1,
            "column": 1,
            "message": "Expression nests too deeply to parse",
            "stage": "Parse error",
            "severity": "error",
        }]
    return []


def main(argv):
    if len(argv) < 2:
        print(
            "Usage: art_check.py [--root DIR] (<script.art> | --stdin)",
            file=sys.stderr,
        )
        return 2

    if argv[1] == "--stdin":
        source = sys.stdin.read()
    else:
        path = argv[1]
        if not os.path.isfile(path):
            print(f"No such file: {path}", file=sys.stderr)
            return 2
        with open(path, "r") as f:
            source = f.read()

    json.dump({"diagnostics": check(source)}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
