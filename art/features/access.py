"""Property/index access: `obj.name`, `obj.name = v`, `obj[i]`,
`obj[i] = v`, and `super` (as a bare primary - `super.method()` reads
as a Get with `Super()` as the object; the constructor-call form
`super(args)` is handled in calls.py since it's Call-shaped)."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError, ReturnSignal
from ..tokens import TokenType, register_keyword
from ..parser.registry import postfix_parser, primary_parser, assignment_target
from ..interpreter.registry import eval_handler
from ..runtime import Environment, LangInstance, LangTable, LangModule, LangEnum, LangClass, BoundMethod, PrimitiveBoundMethod
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser

register_keyword("super", TokenType.SUPER)

# `"hi".upper()` / `16.sqrt()` / `numbers.push(4)` sugar (see
# PrimitiveBoundMethod): which global namespace table a value's `.name`
# is looked up in when the value has no such property of its own.
# Deliberately narrow - only the types that actually have a
# namespace-table library (std/string.art, std/math.art, std/table.art)
# get this treatment; everything else falls through to the ordinary
# property-access error below, same as ever.
_PRIMITIVE_NAMESPACES = (
    (str, "string"),
    (LangTable, "table"),
    ((int, float), "math"),
)


def _primitive_namespace_for(value):
    if isinstance(value, bool):
        return None  # bool is an int subclass in Python - not a math value here
    for types, namespace_name in _PRIMITIVE_NAMESPACES:
        if isinstance(value, types):
            return namespace_name
    return None


def _namespace_method(interp: "Interpreter", env, value, name):
    """Resolve `value.name` as a library method from `value`'s namespace
    table, or return None if this kind of value has no namespace."""
    namespace_name = _primitive_namespace_for(value)
    if namespace_name is None:
        return None

    if not env.has(namespace_name):
        raise LangRuntimeError(
            f"'{namespace_name}' isn't loaded, so {interp._type_name(value)} "
            f"values have no methods available"
        )

    namespace = env.get(namespace_name)
    if not isinstance(namespace, LangTable):
        raise LangRuntimeError(f"'{namespace_name}' isn't a namespace table")

    if name not in namespace.map:
        if isinstance(value, LangTable):
            raise LangRuntimeError(
                f"Table has no entry '{name}', and the 'table' library "
                f"has no method by that name either"
            )
        raise LangRuntimeError(
            f"{interp._type_name(value)} values have no method '{name}' "
            f"(nothing named '{name}' in the '{namespace_name}' library)"
        )

    return PrimitiveBoundMethod(value, namespace.map[name])


class Get(Node):
    def __init__(self, obj, name):
        self.obj = obj
        self.name = name

    def __repr__(self):
        return f"Get({self.obj!r}.{self.name})"


class Set(Node):
    def __init__(self, obj, name, value):
        self.obj = obj
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Set({self.obj!r}.{self.name} = {self.value!r})"


class Index(Node):
    def __init__(self, obj, index):
        self.obj = obj
        self.index = index

    def __repr__(self):
        return f"Index({self.obj!r}[{self.index!r}])"


class IndexSet(Node):
    def __init__(self, obj, index, value):
        self.obj = obj
        self.index = index
        self.value = value

    def __repr__(self):
        return f"IndexSet({self.obj!r}[{self.index!r}] = {self.value!r})"


class Super(Node):
    def __repr__(self):
        return "Super()"


# ---------- parsing ----------

@primary_parser(TokenType.SUPER)
def _parse_super(parser: "Parser"):
    parser._advance()
    return Super()


@postfix_parser(TokenType.DOT)
def _parse_get(parser: "Parser", left):
    parser._advance()  # consume '.'
    name = parser._consume(TokenType.IDENTIFIER, "Expected property name after '.'").lexeme
    return Get(left, name)


@postfix_parser(TokenType.LBRACKET)
def _parse_index(parser: "Parser", left):
    parser._advance()  # consume '['
    index = parser._expression()
    parser._consume(TokenType.RBRACKET, "Expected ']' after index")
    return Index(left, index)


@assignment_target(Get)
def _get_to_set(target: Get, value):
    return Set(target.obj, target.name, value)


@assignment_target(Index)
def _index_to_index_set(target: Index, value):
    return IndexSet(target.obj, target.index, value)


# ---------- interpreting ----------

@eval_handler(Get)
def _eval_get(interp: "Interpreter", node: Get, env):
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
        # An entry the table actually holds always wins over a library
        # method, so a table storing its own "sort" key still reads back
        # what it stores.
        if node.name in obj.map:
            return obj.map[node.name]
        return _namespace_method(interp, env, obj, node.name)

    if isinstance(obj, LangModule):
        return obj.get(node.name)

    if isinstance(obj, LangEnum):
        if node.name == "members":
            return obj.get_members()
        return obj.get(node.name)

    if isinstance(obj, LangClass):
        if obj.find_static_owner(node.name) is not None:
            return obj.get_static(node.name)
        static_method = obj.find_static_method(node.name)
        if static_method is not None:
            return static_method
        if node.name in obj.nested_classes:
            return obj.nested_classes[node.name]
        raise LangRuntimeError(
            f"Class '{obj.name}' has no static field, static method or "
            f"nested class '{node.name}'"
        )

    method = _namespace_method(interp, env, obj, node.name)
    if method is not None:
        return method
    
    raise LangRuntimeError(f"Cannot access property '{node.name}' on {obj!r}")


@eval_handler(Set)
def _eval_set(interp: "Interpreter", node: Set, env):
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
def _eval_index(interp: "Interpreter", node: Index, env):
    obj = interp._eval(node.obj, env)
    index = interp._eval(node.index, env)

    if isinstance(obj, LangTable):
        return obj.get(index)

    raise LangRuntimeError(f"Cannot index {obj!r}")


@eval_handler(IndexSet)
def _eval_index_set(interp: "Interpreter", node: IndexSet, env):
    obj = interp._eval(node.obj, env)
    index = interp._eval(node.index, env)
    value = interp._eval(node.value, env)

    if isinstance(obj, LangTable):
        obj.set(index, value)
        return value

    raise LangRuntimeError(f"Cannot assign through index on {obj!r}")


@eval_handler(Super)
def _eval_super(interp: "Interpreter", node: Super, env):
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
        raise LangRuntimeError(f"Class '{current_class.name}' has no superclass")

    return superclass