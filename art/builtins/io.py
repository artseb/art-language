"""Console output builtins."""
from typing import TYPE_CHECKING

from . import native
from ..runtime.values import stringify

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter


@native("print", arity=1)
def _print(interp: "Interpreter", args):
    print(stringify(args[0]))
    return None
