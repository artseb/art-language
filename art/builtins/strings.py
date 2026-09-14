"""Native string primitives. These are intentionally NOT the public
API - notice the `__native_string_` prefix on every registered name.
The public API is the `string` table built in std/string.art (plain
ART source, wrapping these), so `string.upper(x)` and `"hi".upper()`
both go through ART code before they ever reach here. Nothing about
that wrapping needs these functions to be hidden per se - it's a
naming convention, not real privacy - but it keeps a script's global
namespace from being cluttered with names most scripts should only
ever reach via `string.___`.

`len()` is the one exception, kept as a bare global rather than
`string.length`/`table` since "how many things are in this" isn't
really a string-specific or table-specific operation - it's closer to
a language primitive (compare Python's own bare `len()`).
"""
from . import native
from ..errors import LangRuntimeError
from ..runtime import LangTable, stringify


def _require_string(name, value, position="argument"):
    if not isinstance(value, str):
        raise LangRuntimeError(
            f"{name}() expects a string {position}, got {type(value).__name__}"
        )
    return value


@native("len")
def _len(interp, args):
    """len(x) -> Number. Works on strings and tables (array part +
    map part) - deliberately not string-only, since "how many things
    are in this" is the same question either way."""
    if len(args) != 1:
        raise LangRuntimeError(f"len() expects 1 argument, got {len(args)}")

    value = args[0]

    if isinstance(value, str):
        return float(len(value))

    if isinstance(value, LangTable):
        return float(len(value.array) + len(value.map))

    raise LangRuntimeError(f"len() expects a string or table, got {type(value).__name__}")


@native("__native_string_upper", arity=1)
def _upper(interp, args):
    return _require_string("upper", args[0]).upper()


@native("__native_string_lower", arity=1)
def _lower(interp, args):
    return _require_string("lower", args[0]).lower()


@native("__native_string_trim", arity=1)
def _trim(interp, args):
    return _require_string("trim", args[0]).strip()


@native("__native_string_contains", arity=2)
def _contains(interp, args):
    haystack = _require_string("contains", args[0])
    needle = _require_string("contains", args[1], "second argument")
    return needle in haystack


@native("__native_string_replace", arity=3)
def _replace(interp, args):
    text = _require_string("replace", args[0])
    old = _require_string("replace", args[1], "second argument")
    new = _require_string("replace", args[2], "third argument")
    return text.replace(old, new)


@native("__native_string_split")
def _split(interp, args):
    """__native_string_split(s) -> splits on any whitespace.
    __native_string_split(s, sep) -> splits on the given separator."""
    if len(args) not in (1, 2):
        raise LangRuntimeError(f"split() expects 1 or 2 arguments, got {len(args)}")

    text = _require_string("split", args[0])
    pieces = text.split(args[1]) if len(args) == 2 and args[1] else text.split()

    table = LangTable()
    for piece in pieces:
        table.append(piece)
    return table


@native("__native_string_join", arity=2)
def _join(interp, args):
    table, sep = args[0], args[1]

    if not isinstance(table, LangTable):
        raise LangRuntimeError(f"join() expects a table as its first argument, got {type(table).__name__}")
    _require_string("join", sep, "second argument")

    return sep.join(stringify(item) for item in table.array)


@native("__native_string_substring", arity=3)
def _substring(interp, args):
    """__native_string_substring(s, start, end) - 1-indexed and
    inclusive on both ends, matching how table indexing already works
    elsewhere in ART, rather than Python's 0-indexed/exclusive-end
    slicing."""
    text = _require_string("substring", args[0])
    start, end = args[1], args[2]

    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        raise LangRuntimeError("substring() expects numeric start/end")

    start_index = max(int(start) - 1, 0)
    end_index = min(int(end), len(text))
    return text[start_index:end_index]