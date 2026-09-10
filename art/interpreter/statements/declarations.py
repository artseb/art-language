"""Declarations that introduce a new name into scope: functions,
classes, enums, and the `local a, b = ...` multi-assign form."""
from ...ast import FunDecl, ClassDecl, EnumDecl, MultiAssign
from ...errors import LangRuntimeError
from ...runtime import Environment, LangClass, LangInstance, LangEnum
from ..registry import exec_handler


@exec_handler(MultiAssign)
def _exec_multi_assign(interp, node, env):
    values = []

    for expr in node.values:
        value = interp._eval(expr, env)

        if isinstance(value, tuple):
            values.extend(value)
        else:
            values.append(value)

    for index, name in enumerate(node.names):
        value = values[index] if index < len(values) else None

        if name == "_":
            continue

        if node.is_local:
            env.define(name, value)
        else:
            env.assign_existing_or_global(name, value)


@exec_handler(FunDecl)
def _exec_fun_decl(interp, node, env):
    interp._register_overload(
        env.values, node.name, node.params, node.body, env, node.return_type
    )


@exec_handler(ClassDecl)
def _exec_class_decl(interp, node, env):
    klass = interp._build_class(node, env)

    if node.is_local:
        env.define(node.name, klass)
    else:
        env.assign_existing_or_global(node.name, klass)


@exec_handler(EnumDecl)
def _exec_enum_decl(interp, node, env):
    class_env = Environment(env)

    klass = LangClass(
        node.name,
        None,
        [],
        class_env,
    )

    klass.is_enum = True
    class_env.define("__class", klass)

    # Build enum methods and constructor.
    for member in node.body:
        if isinstance(member, FunDecl):
            interp._register_overload(
                klass.methods, member.name, member.params, member.body,
                class_env, member.return_type,
            )

    enum = LangEnum(node.name, klass)

    # Construct each enum member.
    for member in node.members:
        instance = LangInstance(klass)

        constructor = klass.methods.get(node.name)

        if constructor is not None:
            args = [
                interp._eval(arg, env)
                for arg in member.args
            ]

            interp._call_function(
                constructor,
                args,
                this=instance,
            )
        elif member.args:
            raise LangRuntimeError(
                f"Enum '{node.name}' has no constructor "
                f"for member '{member.name}'"
            )

        instance.enum_name = node.name
        instance.enum_member_name = member.name
        interp._make_immutable(instance)

        enum.add_member(member.name, instance)

    if node.is_local:
        env.define(node.name, enum)
    else:
        env.assign_existing_or_global(node.name, enum)
