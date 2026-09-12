"""
Registry for ART's native (Python-implemented) global functions.

The point of this package: adding a new builtin should mean "drop a new
file in here", not "go edit the interpreter's Call-handling code". Each
module below owns one small area of functionality and registers its
functions with the `@native(...)` decorator - nothing imports those
modules directly; `install()` discovers and loads every module in this
package automatically, so a file that's never explicitly imported still
takes effect just by existing here.

    # art/builtins/my_area.py
    from . import native

    @native("greet")
    def _greet(interp, args):
        return "hello, " + args[0]

That's the whole integration surface. No other file needs to change.
"""
import pkgutil
import importlib

from ..runtime.functions import NativeFunction

_REGISTRY = {}
_loaded = False


def native(name, arity=None):
    """Decorator: register `fn` as the ART builtin `name`.

    `arity`, if given, is the exact number of arguments the builtin
    accepts; NativeFunction enforces it before `fn` ever runs. Leave it
    None for a variadic builtin that wants to check argument count (or
    types) itself.
    """
    def decorator(fn):
        if name in _REGISTRY:
            raise RuntimeError(
                f"Builtin '{name}' is already registered "
                f"(second registration from {fn.__module__}.{fn.__name__})"
            )
        _REGISTRY[name] = NativeFunction(name, fn, arity)
        return fn
    return decorator


def _load_all():
    global _loaded
    if _loaded:
        return
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{module_name}")
    _loaded = True


def install(environment):
    """Populate `environment` (normally the interpreter's global scope)
    with every registered builtin. Safe to call more than once."""
    _load_all()
    for name, func in _REGISTRY.items():
        environment.define(name, func)
