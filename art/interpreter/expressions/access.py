"""Property/index access: `obj.name`, `obj.name = v`, `obj[i]`,
`obj[i] = v`, and `super` as a bare expression (e.g. passed to
`super.method()` via Get, handled below)."""
from ...ast import Get, Set, Index, IndexSet, Super
from ...errors import LangRuntimeError
from ...runtime import Environment, LangInstance, LangTable, LangModule, LangEnum, LangClass, BoundMethod
from ...errors import ReturnSignal
from ..registry import eval_handler


@eval_handler(Get)
def _eval_get(interp, node, env):
    obj = interp._eval(node.obj, env)

    if isinstance(node.obj, Super):
        if not isinstance(obj, LangClass):
            raise LangRuntimeError("Invalid superclass")

        method = obj.find_method(node.name)

        if method is None:
            raise LangRuntimeError(
                f"Superclass '{obj.name}' has no method '{node.name}'"
            )

        this = env.get("this")
        return BoundMethod(this, method)

    if isinstance(obj, LangInstance):
        if obj.is_enum_member:
            if node.name == "name":
                return obj.enum_member_name

            if node.name == "enum":
                return obj.enum_name

        owner = obj.klass.find_getter_owner(node.name)

        if owner is not None:
            getter = owner.getters[node.name]
            getter_env = Environment(owner.closure)
            getter_env.define("this", obj)

            try:
                interp._exec(getter.body, getter_env)
            except ReturnSignal as signal:
                return signal.value

            return None

        return obj.get(node.name)

    if isinstance(obj, LangTable):
        return obj.get(node.name)

    if isinstance(obj, LangModule):
        return obj.get(node.name)

    if isinstance(obj, LangEnum):
        if node.name == "members":
            return obj.get_members()
        return obj.get(node.name)

    if isinstance(obj, LangClass):
        if obj.find_static_owner(node.name) is not None:
            return obj.get_static(node.name)
        if node.name in obj.nested_classes:
            return obj.nested_classes[node.name]
        raise LangRuntimeError(
            f"Class '{obj.name}' has no static field or nested class '{node.name}'"
        )

    raise LangRuntimeError(
        f"Cannot access property '{node.name}' on {obj!r}"
    )


@eval_handler(Set)
def _eval_set(interp, node, env):
    obj = interp._eval(node.obj, env)
    value = interp._eval(node.value, env)
    if isinstance(obj, LangInstance):
        if obj.is_enum_member:
            raise LangRuntimeError(
                f"Cannot modify enum member '{obj.enum_name}.{obj.enum_member_name}'"
            )

        owner = obj.klass.find_setter_owner(node.name)
        if owner is not None:
            setter = owner.setters[node.name]
            setter_env = Environment(owner.closure)
            setter_env.define("this", obj)
            setter_env.define(setter.param.name, value)
            interp._exec(setter.body, setter_env)
            return value

        obj.set(node.name, value)
    elif isinstance(obj, LangTable):
        obj.set(node.name, value)
    elif isinstance(obj, LangClass):
        obj.set_static(node.name, value)
    else:
        raise LangRuntimeError(f"Cannot set property '{node.name}' on {obj!r}")
    return value


@eval_handler(Index)
def _eval_index(interp, node, env):
    obj = interp._eval(node.obj, env)
    index = interp._eval(node.index, env)

    if isinstance(obj, LangTable):
        return obj.get(index)

    raise LangRuntimeError(f"Cannot index {obj!r}")


@eval_handler(IndexSet)
def _eval_index_set(interp, node, env):
    obj = interp._eval(node.obj, env)
    index = interp._eval(node.index, env)
    value = interp._eval(node.value, env)

    if isinstance(obj, LangTable):
        obj.set(index, value)
        return value

    raise LangRuntimeError(f"Cannot assign through index on {obj!r}")


@eval_handler(Super)
def _eval_super(interp, node, env):
    if not env.has("this"):
        raise LangRuntimeError("'super' can only be used inside a class method")

    if not env.has("__class"):
        raise LangRuntimeError("Cannot determine superclass for 'super'")

    this = env.get("this")
    current_class = env.get("__class")

    if not isinstance(this, LangInstance):
        raise LangRuntimeError("'super' requires a class instance")

    superclass = current_class.superclass

    if superclass is None:
        raise LangRuntimeError(
            f"Class '{current_class.name}' has no superclass"
        )

    return superclass
