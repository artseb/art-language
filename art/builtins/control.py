"""Control-flow-ish builtins that need to call back into the interpreter
(as opposed to `io.py`, which is pure Python once it has its arguments)."""
from typing import TYPE_CHECKING

from . import native
from ..errors import LangRuntimeError

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter


@native("attempt")
def _attempt(interp: "Interpreter", args):
    """attempt(callee, ...args) -> (result, error_message)

    Calls `callee` with the remaining arguments and never lets a
    LangRuntimeError propagate; instead it comes back as the second
    element of the returned pair, `nil` on success. ART code typically
    unpacks it: `local ok, err = attempt(risky, 1, 2)`.
    """
    if not args:
        raise LangRuntimeError("attempt() expects at least 1 argument")

    callee, rest = args[0], args[1:]

    try:
        return interp.call_value(callee, rest), None
    except LangRuntimeError as error:
        return None, error.message
