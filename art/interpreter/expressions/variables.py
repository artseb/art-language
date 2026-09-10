"""Reading and writing plain variables, including the implicit
`this.field` fallback that lets a method body refer to `field` instead
of always spelling out `this.field`."""
from ...ast import Variable, Assign
from ...errors import LangRuntimeError
from ...runtime import LangInstance
from ..registry import eval_handler


@eval_handler(Variable)
def _eval_variable(interp, node, env):
    if env.has(node.name):
        return env.get(node.name)
    # fallback: implicit `this.field` / `this.staticField` access
    # inside a method body
    if env.has("this"):
        this = env.get("this")
        if isinstance(this, LangInstance):
            if node.name in this.fields:
                return this.fields[node.name]
            static_owner = this.klass.find_static_owner(node.name)
            if static_owner is not None:
                return static_owner.static_fields[node.name]
    raise LangRuntimeError(f"Undefined variable '{node.name}'")


@eval_handler(Assign)
def _eval_assign(interp, node, env):
    value = interp._eval(node.value, env)

    if node.name == "_":
        return value

    if node.is_local:
        env.define(node.name, value)
    else:
        # implicit `this.field = ...` / `this.staticField = ...`
        # inside a method body, if it's a field
        if env.has("this") and not env.has(node.name):
            this = env.get("this")
            if isinstance(this, LangInstance):
                static_owner = this.klass.find_static_owner(node.name)
                if static_owner is not None:
                    static_owner.static_fields[node.name] = value
                else:
                    this.fields[node.name] = value
                return value

        env.assign_existing_or_global(node.name, value)

    return value
