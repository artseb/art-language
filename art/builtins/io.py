"""Console output builtins."""
from typing import TYPE_CHECKING

from . import native

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter


@native("print", arity=None)
def _print(interp: "Interpreter", args):
    finalString = ""
    for arg in args:
        stringified = interp.display(arg)
        finalString += stringified + " "
    print(finalString)
    return None