"""Native math primitives - thin wrappers over Python's own `math`
module. Like strings.py, these are registered under a `__native_math_`
prefix and aren't meant to be called directly; the public API is the
`math` table built in std/math.art."""
import math

from . import native
from ..errors import LangRuntimeError


def _require_number(name, value, position="argument"):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise LangRuntimeError(
            f"{name}() expects a number {position}, got {type(value).__name__}"
        )
    return value


@native("__native_math_sqrt", arity=1)
def _sqrt(interp, args):
    value = _require_number("sqrt", args[0])
    if value < 0:
        raise LangRuntimeError("sqrt() expects a non-negative number")
    return math.sqrt(value)


@native("__native_math_pow", arity=2)
def _pow(interp, args):
    base = _require_number("pow", args[0])
    exponent = _require_number("pow", args[1], "second argument")
    return float(base ** exponent)


@native("__native_math_abs", arity=1)
def _abs(interp, args):
    return abs(_require_number("abs", args[0]))


@native("__native_math_floor", arity=1)
def _floor(interp, args):
    return float(math.floor(_require_number("floor", args[0])))


@native("__native_math_ceil", arity=1)
def _ceil(interp, args):
    return float(math.ceil(_require_number("ceil", args[0])))


@native("__native_math_round", arity=1)
def _round(interp, args):
    return float(round(_require_number("round", args[0])))


@native("__native_math_min", arity=2)
def _min(interp, args):
    return min(_require_number("min", args[0]), _require_number("min", args[1], "second argument"))


@native("__native_math_max", arity=2)
def _max(interp, args):
    return max(_require_number("max", args[0]), _require_number("max", args[1], "second argument"))