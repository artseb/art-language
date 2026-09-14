"""Auto-loading ART's standard library: plain `.art` files in `std/`,
executed directly into a scope - no `import` needed, and no namespace
wrapper either (contrast with `import "file.art"` in modules.py, which
builds an isolated LangModule so you reach its contents as
`file.thing`). A class in std/vector.art becomes plain global `Vector`,
not `std.Vector`.

That's deliberate, not just convenience: the point is that the
standard library IS ordinary ART source. Someone learning the language
can open std/vector.art and read a real class with real operator
overloads - the documentation and the implementation are the same
file. Keeping it import-free means it reads as part of the language
rather than a library you have to know to reach for.

Runs once per process (parsing is cached at module level - see
_std_programs()), then its already-parsed statements are executed
fresh into whichever scope asks for it (every Interpreter's globals,
and every module's isolated scope too - see core.py and modules.py).
"""
import os
from typing import TYPE_CHECKING

from ..errors import ArtError, LangRuntimeError

if TYPE_CHECKING:
    from .core import Interpreter

# Sibling of the `art` package itself - the language's own stdlib,
# always in the same place relative to the interpreter's own code,
# regardless of the user's project directory or working directory.
STD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "std",
)

_std_programs_cache = None  # list[(filename, [Stmt, ...])], filled in lazily


def _std_programs():
    global _std_programs_cache

    if _std_programs_cache is not None:
        return _std_programs_cache

    from ..lexer import Lexer
    from ..parser import Parser

    programs = []

    if os.path.isdir(STD_DIR):
        for filename in sorted(os.listdir(STD_DIR)):
            if not filename.endswith(".art"):
                continue

            path = os.path.join(STD_DIR, filename)
            try:
                with open(path, "r") as f:
                    source = f.read()
                tokens = Lexer(source).tokenize()
                ast = Parser(tokens).parse()
            except ArtError as e:
                raise LangRuntimeError(f"While loading standard library '{filename}': {e}")

            programs.append((filename, ast))

    _std_programs_cache = programs
    return programs


class StdlibMixin:
    def _install_stdlib(self: "Interpreter", env):
        """Run every std/*.art file's top-level statements directly
        into `env`. Call this AFTER native builtins are already in
        `env` - stdlib source is free to call print/sqrt/etc. the same
        as any other ART code, and needs them to already be there."""
        for filename, statements in _std_programs():
            try:
                for stmt in statements:
                    self._exec(stmt, env)
            except ArtError as e:
                raise LangRuntimeError(f"While loading standard library '{filename}': {e}")