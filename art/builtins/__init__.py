import pkgutil
import importlib

from ..runtime.functions import NativeFunction

_REGISTRY = {}
_loaded = False


def native(name, arity=None):
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
