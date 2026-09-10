from ..errors import LangRuntimeError, ReturnSignal
from ..runtime import (
    Environment, LangFunction, BoundMethod, LangClass, LangEnum,
    NativeFunction, runtime_type_matches,
)


class CallingMixin:
    def call_value(self, callee, args):
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

    @staticmethod
    def _register_overload(store, name, params, body, closure, return_type=None, display_name=None):
        existing = store.get(name)
        if not isinstance(existing, LangFunction):
            existing = LangFunction(display_name or name)
            store[name] = existing
        existing.add_overload(params, body, closure, return_type)
        return existing

    def _call_function(self, func: LangFunction, args, this):
        params, body, closure, return_type = self._resolve_overload(func, args)

        call_env = Environment(closure)

        if this is not None:
            call_env.define("this", this)

        arg_index = 0

        for param in params:
            if param.variadic:
                from ..runtime import LangTable
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

    def _resolve_overload(self, func: LangFunction, args):
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
