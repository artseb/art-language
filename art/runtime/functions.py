class LangFunction:
    def __init__(self, name):
        self.name = name
        self.overloads = []  # list of (list[Param], Block, Environment, return_type)

    def add_overload(self, params, body, closure, return_type=None):
        self.overloads.append((params, body, closure, return_type))

    def __repr__(self):
        return f"<fun {self.name}, {len(self.overloads)} overload(s)>"

class BoundMethod:
    def __init__(self, instance, func: LangFunction):
        self.instance = instance
        self.func = func


class PrimitiveBoundMethod:
    """The `"hi".upper()` sugar: for a raw value that isn't a
    LangInstance (a string, a number - see features/access.py's Get
    handler for exactly which), `.name` is resolved by looking `name`
    up in that type's namespace table (`string`, `math` - ordinary ART
    tables, see std/string.art and std/math.art) rather than on the
    value itself. Calling it then passes the original value as the
    function's first argument.

    Unlike BoundMethod, there's no `this` binding involved - the
    functions living in those namespace tables are just plain ART
    functions that take the receiver as an explicit first parameter
    (`fun(s) { ... }`), the same as if you'd written `string.upper(s)`
    yourself. This is purely a call-site convenience, not a different
    calling convention.
    """
    def __init__(self, receiver, func):
        self.receiver = receiver
        self.func = func

    def __repr__(self):
        return f"<bound {self.func!r} to {self.receiver!r}>"

class NativeFunction:
    """A builtin implemented in Python rather than ART source - `print`,
    `attempt`, etc. Registered by the modules under `art/builtins/`; see
    that package for how a new one gets added.

    `fn` is called as `fn(interpreter, args)` and returns the ART-level
    result directly (already evaluated args in, a plain value out - no
    AST/Environment involved).
    """
    def __init__(self, name, fn, arity=None):
        self.name = name
        self.fn = fn
        self.arity = arity  # None = any number of args; an int pins it

    def call(self, interpreter, args):
        if self.arity is not None and len(args) != self.arity:
            from ..errors import LangRuntimeError
            plural = "" if self.arity == 1 else "s"
            raise LangRuntimeError(
                f"{self.name}() expects {self.arity} argument{plural}, got {len(args)}"
            )
        return self.fn(interpreter, args)

    def __repr__(self):
        return f"<native fn {self.name}>"