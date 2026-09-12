"""Reading and writing plain variables: `name`, `name = value`,
`local name = value`, plus the implicit `this.field` fallback that lets
a method body say `field` instead of always spelling out `this.field`."""
from typing import TYPE_CHECKING

from ..errors import LangRuntimeError
from ..tokens import TokenType
from ..parser.registry import primary_parser, assignment_target
from ..interpreter.registry import eval_handler
from ..runtime import LangInstance
from .base import Node

if TYPE_CHECKING:
    from ..interpreter.core import Interpreter
    from ..parser.core import Parser


class Variable(Node):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Variable({self.name})"


class Assign(Node):
    def __init__(self, name, value, is_local=False, is_static=False):
        self.name = name
        self.value = value
        self.is_local = is_local
        self.is_static = is_static

    def __repr__(self):
        return f"Assign({self.name}, {self.value!r}, local={self.is_local})"


# ---------- parsing ----------

@primary_parser(TokenType.IDENTIFIER)
def _parse_variable(parser: "Parser"):
    parser._advance()
    return Variable(parser._previous().lexeme)


@assignment_target(Variable)
def _variable_to_assign(target: Variable, value):
    return Assign(target.name, value, is_local=False)


# ---------- interpreting ----------

@eval_handler(Variable)
def _eval_variable(interp: "Interpreter", node: Variable, env):
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
def _eval_assign(interp: "Interpreter", node: Assign, env):
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
