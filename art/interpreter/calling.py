"""Everything about invoking something callable: user-defined functions
(with overload resolution), bound methods, class constructors, and
native builtins. This is engine machinery shared by many feature files
(calls.py, classes_.py, enums.py, imports_.py, the `attempt` builtin,
operator-overload dispatch in operators.py...) so it lives on the
Interpreter itself rather than as a self-registered handler for one
specific node type - there's no single node type it belongs to."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError, ReturnSignal
from ..runtime import (
    Environment, LangFunction, BoundMethod, LangClass, LangInstance, LangEnum,
    NativeFunction, LangTable, runtime_type_matches,
)

if TYPE_CHECKING:
    from .core import Interpreter


class CallingMixin:
    def call_value(self: "Interpreter", callee, args):
        """Call anything ART considers callable and return its result.
        The single place that knows how to dispatch on callee type -
        calls.py's Call handler and the `attempt` builtin both route
        through this instead of duplicating the isinstance chain."""
        if isinstance(callee, LangFunction):
            return self._call_function(callee, args, this=None)

        if isinstance(callee, BoundMethod):
            return self._call_function(callee.func, args, this=callee.instance)

        if isinstance(callee, NativeFunction):
            return callee.call(self, args)

        if isinstance(callee, LangClass):
            if callee.is_enum:
                raise LangRuntimeError(
                    f"Cannot instantiate enum '{callee.name}' directly"
                )
            return self._instantiate(callee, args)

        if isinstance(callee, LangEnum):
            raise LangRuntimeError(
                f"Cannot instantiate enum '{callee.name}' directly"
            )

        raise LangRuntimeError(f"'{callee!r}' is not callable")

    def _instantiate(self: "Interpreter", klass: LangClass, args):
        """Build a new instance of `klass`: run every field initializer
        (inherited ones included - see LangClass.find_field_inits),
        then call the constructor (a method named the same as the
        class) if one exists. Used for plain `SomeClass(...)` calls;
        enums build their members the same way but call this directly
        rather than going through call_value (see enums.py)."""
        instance = LangInstance(klass)

        for name, init_expr in klass.find_field_inits():
            instance.fields[name] = self._eval(init_expr, klass.closure)

        constructor = klass.methods.get(klass.name)
        if constructor is not None:
            self._call_function(constructor, args, this=instance)

        return instance

    @staticmethod
    def _register_overload(store, name, params, body, closure, return_type=None, display_name=None):
        """Add one overload of `name` to `store` (a dict, or anything with
        `.get`/`__setitem__` like an Environment's `.values`), creating the
        LangFunction the first time `name` is seen. This is the one place
        that knows how "a function with this name already exists? then add
        an overload; otherwise create it" works - shared by plain function
        declarations (functions.py), class methods/operators (classes_.py),
        and enum constructors (enums.py).
        """
        existing = store.get(name)
        if not isinstance(existing, LangFunction):
            existing = LangFunction(display_name or name)
            store[name] = existing
        existing.add_overload(params, body, closure, return_type)
        return existing

    def _call_function(self: "Interpreter", func: LangFunction, args, this):
        params, body, closure, return_type = self._resolve_overload(func, args)

        call_env = Environment(closure)

        if this is not None:
            call_env.define("this", this)

        arg_index = 0

        for param in params:
            if param.variadic:
                values = LangTable()

                while arg_index < len(args):
                    values.append(args[arg_index])
                    arg_index += 1

                call_env.define(param.name, values)
                break

            if arg_index < len(args):
                value = args[arg_index]
                arg_index += 1
            else:
                value = self._eval(param.default, call_env)

            call_env.define(param.name, value)

        try:
            self._exec(body, call_env)
        except ReturnSignal as r:
            if return_type is not None:
                if not runtime_type_matches(r.value, return_type):
                    raise LangRuntimeError(
                        f"Function '{func.name}' expected return type "
                        f"'{return_type}', got {type(r.value).__name__}"
                    )
            return r.value

        if return_type is not None:
            if not runtime_type_matches(None, return_type):
                raise LangRuntimeError(
                    f"Function '{func.name}' expected return type "
                    f"'{return_type}', got nil"
                )

        return None

    def _resolve_overload(self: "Interpreter", func: LangFunction, args):
        candidates = []

        for overload in func.overloads:
            params = overload[0]

            variadic = params and params[-1].variadic

            required = sum(
                1 for param in params
                if param.default is None and not param.variadic
            )

            if variadic:
                if len(args) >= required:
                    candidates.append(overload)
            else:
                if required <= len(args) <= len(params):
                    candidates.append(overload)

        if not candidates:
            raise LangRuntimeError(
                f"No overload of '{func.name}' takes {len(args)} argument(s)"
            )

        matching = [
            (params, body, closure, return_type)
            for params, body, closure, return_type in candidates
            if all(
                runtime_type_matches(arg, p.type_name)
                for p, arg in zip(params, args)
            )
        ]

        if matching:
            def specificity(overload):
                params = overload[0]
                return sum(1 for p in params if p.type_name is not None)
            return max(matching, key=specificity)

        return candidates[0]
