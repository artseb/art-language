from . import native
from ..runtime.values import stringify


@native("print", arity=1)
def _print(interp, args):
    print(stringify(args[0]))
    return None
