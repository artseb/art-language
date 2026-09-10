from . import native
from ..errors import LangRuntimeError


@native("attempt")
def _attempt(interp, args):
    if not args:
        raise LangRuntimeError("attempt() expects at least 1 argument")

    callee, rest = args[0], args[1:]

    try:
        return interp.call_value(callee, rest), None
    except LangRuntimeError as error:
        return None, error.message
