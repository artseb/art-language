import sys
import os
import threading

from art.lexer import Lexer
from art.parser import Parser
from art.interpreter import Interpreter
from art.errors import ArtError

# Each ART-level function call costs several Python stack frames (through
# _call_function -> _exec -> ... -> _eval), so Python's default recursion
# limit (1000) and default thread stack size let a *completely ordinary*,
# non-buggy recursive ART function (e.g. summing to a few hundred) hit a
# stack overflow. Raising sys.setrecursionlimit() alone is not safe here -
# without a correspondingly larger C stack, deep recursion can segfault
# the process instead of raising a catchable Python exception. Running the
# interpreter on a dedicated thread with an explicit, larger stack size is
# the standard safe way to give ART scripts reasonable recursion headroom.
#
# threading.stack_size() enforces different, undocumented limits per
# platform (some Windows builds reject exactly 256 MiB outright, raising
# ValueError), so rather than assuming one size works everywhere, try
# progressively smaller sizes and use whichever one the OS actually
# accepts. If none of them can be set, fall back to Python's own defaults
# entirely rather than raising the recursion limit without a stack to
# back it up. The recursion limit paired with each stack size is picked
# with a large safety margin below what was empirically observed safe on
# a 256 MiB stack (RecursionError still fired cleanly well past 800,000
# nested calls there) - platforms with heavier per-frame stack usage than
# this one still have plenty of room.
_STACK_TIERS = [
    (256 * 1024 * 1024, 100_000),
    (128 * 1024 * 1024, 50_000),
    (64 * 1024 * 1024, 25_000),
    (32 * 1024 * 1024, 12_000),
    (16 * 1024 * 1024, 6_000),
    (8 * 1024 * 1024, 3_000),
]


def _pick_stack_size():
    """Try each stack-size tier (largest first) and return
    (stack_size_bytes, recursion_limit) for the first one the platform
    accepts, or (None, None) if none of them can be set at all."""
    for size_bytes, recursion_limit in _STACK_TIERS:
        try:
            threading.stack_size(size_bytes)
        except (ValueError, RuntimeError):
            continue
        return size_bytes, recursion_limit
    return None, None


def _run_with_headroom(target):
    """Run `target` (a zero-arg callable) on a thread with a larger stack
    and higher recursion limit where the platform allows it, then
    re-raise whatever it raised in the calling thread so normal exception
    handling still works."""
    outcome = {}

    def wrapper():
        try:
            target()
        except BaseException as e:  # noqa: BLE001 - deliberately broad, re-raised below
            outcome["error"] = e

    previous_limit = sys.getrecursionlimit()
    previous_stack_size = threading.stack_size()

    _, recursion_limit = _pick_stack_size()
    if recursion_limit is not None:
        sys.setrecursionlimit(max(recursion_limit, previous_limit))

    try:
        thread = threading.Thread(target=wrapper)
        thread.start()
        thread.join()
    finally:
        sys.setrecursionlimit(previous_limit)
        try:
            threading.stack_size(previous_stack_size)
        except (ValueError, RuntimeError):
            pass  # some platforms don't allow resetting this; harmless

    if "error" in outcome:
        raise outcome["error"]


def run_file(path):
    if not os.path.isfile(path):
        print(f"No such file: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r") as f:
        source = f.read()

    base_dir = os.path.dirname(os.path.abspath(path))

    try:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        _run_with_headroom(lambda: Interpreter(base_dir=base_dir).run(ast))

    except ArtError as e:
        # LexError, ParseError, and LangRuntimeError all format themselves
        # as "<Stage> (line N[, column M]): message" - no need to
        # re-prefix here, that would just duplicate the stage name.
        print(str(e), file=sys.stderr)
        sys.exit(1)

    except RecursionError:
        # Guards against runaway ART-level recursion (e.g. a function that
        # calls itself with no base case) crashing the whole interpreter
        # process with a raw Python traceback.
        print("Runtime error: stack overflow (too much recursion)", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        # Anything else is a genuine bug in the interpreter itself, not
        # something the ART script did wrong - but a user staring at a
        # 40-line Python traceback still isn't a good experience. Print a
        # short, clearly-labeled summary; set ART_DEBUG=1 for the full
        # traceback while developing the interpreter itself.
        print(f"Internal interpreter error: {e.__class__.__name__}: {e}", file=sys.stderr)
        if os.environ.get("ART_DEBUG"):
            raise
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 run.py <script.art>", file=sys.stderr)
        sys.exit(1)
    run_file(sys.argv[1])
