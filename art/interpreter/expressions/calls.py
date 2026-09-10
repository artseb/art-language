"""Calling things: `callee(args...)`, `super(args...)` (the constructor
call form, as opposed to `super.method()` which is a Get producing a
BoundMethod - see access.py), and lambda literals.

Actually invoking a resolved callee value is `interp.call_value(...)`
(interpreter/calling.py) - this file's job is just figuring out *what*
is being called and building the resolved callee/args, for every ART
syntax that can appear as `node.callee`.
"""
from ...ast import Call, Super, Lambda
from ...errors import LangRuntimeError
from ...runtime import LangFunction
from ..registry import eval_handler


@eval_handler(Call)
def _eval_call(interp, node, env):
    args = [interp._eval(a, env) for a in node.args]

    if isinstance(node.callee, Super):
        if not env.has("this"):
            raise LangRuntimeError(
                "'super' can only be used inside a class method"
            )

        if not env.has("__class"):
            raise LangRuntimeError(
                "Cannot determine superclass for 'super'"
            )

        current_class = env.get("__class")
        superclass = current_class.superclass

        if superclass is None:
            raise LangRuntimeError(
                f"Class '{current_class.name}' has no superclass"
            )

        constructor = superclass.methods.get(superclass.name)

        if constructor is not None:
            interp._call_function(
                constructor,
                args,
                this=env.get("this"),
            )

        return env.get("this")

    callee = interp._eval(node.callee, env)
    return interp.call_value(callee, args)


@eval_handler(Lambda)
def _eval_lambda(interp, node, env):
    func = LangFunction("<anonymous>")

    func.add_overload(
        node.params,
        node.body,
        env,
        node.return_type,
    )

    return func
