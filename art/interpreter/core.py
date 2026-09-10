import os

from ..errors import LangRuntimeError
from ..runtime import Environment
from .. import builtins as builtins_pkg
from .registry import EXEC_HANDLERS, EVAL_HANDLERS
from .calling import CallingMixin
from .classes import ClassMixin
from .modules import ModuleMixin
from .switching import SwitchMixin

# Importing these packages runs every handler module inside them once,
# which is what actually populates EXEC_HANDLERS / EVAL_HANDLERS above -
# see statements/__init__.py and expressions/__init__.py.
from . import statements as _statements  # noqa: F401  (registration side effect)
from . import expressions as _expressions  # noqa: F401  (registration side effect)


class Interpreter(CallingMixin, ClassMixin, ModuleMixin, SwitchMixin):
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