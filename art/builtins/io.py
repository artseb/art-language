"""Console output builtins."""
from typing import TYPE_CHECKING

from . import native
from ..errors import LangRuntimeError
from ..runtime.values import stringify
from ..runtime.classes import LangInstance

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter


def _display_string(interp: "Interpreter", value):
    """Like stringify(), but gives a class a chance to speak for itself
    first: if `value` is an instance whose class (or a superclass)
    defines `toString()`, that's called with no arguments and its
    result is used instead of the default representation. Anything
    that doesn't define one falls straight through to stringify()."""
    if isinstance(value, LangInstance):
        method = value.klass.find_method("toString")
        if method is not None:
            result = interp._call_function(method, [], this=value)
            if not isinstance(result, str):
                raise LangRuntimeError(
                    f"toString() must return a string, got {type(result).__name__}"
                )
            return result

    return stringify(value)


@native("print", arity=None)
def _print(interp: "Interpreter", args):
    finalString = ""
    for arg in args:
        stringified = _display_string(interp, arg)
        finalString += stringified + " "
    print(finalString)
    return None