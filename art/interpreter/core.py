"""The Interpreter itself: the small, stable engine that ties everything
together. Per-node-type behavior does NOT live here - see registry.py
for how art/features/*.py plug their eval/exec handlers in, and
calling.py / modules.py for the shared engine machinery those handlers
call into (overload resolution, instantiation, module loading - things
used by more than one feature, so they don't belong to any single one).

Adding a new statement or expression type never touches this file:
write a handler function in the right feature file, decorate it with
@exec_handler(...) / @eval_handler(...), and it's live.
"""
import os

from ..errors import LangRuntimeError
from ..runtime import Environment
from .. import builtins as builtins_pkg
from .registry import EXEC_HANDLERS, EVAL_HANDLERS
from .calling import CallingMixin
from .modules import ModuleMixin

# Importing this runs every feature module once, which is what actually
# populates EXEC_HANDLERS / EVAL_HANDLERS above (also, redundantly-but-
# harmlessly, tokens.KEYWORDS and the parser's own registries - see
# art/features/__init__.py).
from .. import features as _features  # noqa: F401  (registration side effect)


class Interpreter(CallingMixin, ModuleMixin):
    def __init__(self, base_dir=None):
        self.globals = Environment()
        builtins_pkg.install(self.globals)

        self.base_dir = base_dir or os.getcwd()
        self.module_cache = {}   # abs_path -> Environment (of that module's globals)
        self._loading = set()    # abs_paths currently mid-import (circular import guard)

    def run(self, statements):
        for stmt in statements:
            self._exec(stmt, self.globals)

    # ---------- dispatch ----------

    def _exec(self, node, env):
        handler = EXEC_HANDLERS.get(type(node))
        if handler is None:
            raise LangRuntimeError(f"No exec handler for {type(node).__name__}")
        return handler(self, node, env)

    def _eval(self, node, env):
        handler = EVAL_HANDLERS.get(type(node))
        if handler is None:
            raise LangRuntimeError(f"No eval handler for {type(node).__name__}")
        return handler(self, node, env)

    # ---------- small value helpers shared across many handlers ----------

    def _truthy(self, value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    @staticmethod
    def _values_equal(left, right):
        # Guards against e.g. `table == table` or `instance == 5` falling
        # through to a Python-level TypeError for types that don't define
        # a sensible `==`.
        try:
            return bool(left == right)
        except TypeError:
            return False

    @staticmethod
    def _type_name(value):
        from ..runtime import LangTable, LangInstance
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "Bool"
        if isinstance(value, float):
            return "Number"
        if isinstance(value, str):
            return "String"
        if isinstance(value, LangTable):
            return "Table"
        if isinstance(value, LangInstance):
            return value.klass.name
        return type(value).__name__
